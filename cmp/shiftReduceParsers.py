from cmp.automata import State, multiline_formatter, empty_formatter
from cmp.pycompiler import Item
from cmp.tools import compute_local_first, compute_firsts, compute_follows
from cmp.utils import ContainerSet

class ShiftReduceParser:
    SHIFT = 'SHIFT'
    REDUCE = 'REDUCE'
    OK = 'OK'
    
    def __init__(self, G, verbose=False):
        self.G = G
        self.verbose = verbose
        self.action = {}
        self.goto = {}
        self._build_parsing_table()
    
    def _build_parsing_table(self):
        raise NotImplementedError()

    def __call__(self, w):
        stack = [ 0 ]
        cursor = 0
        output = []
        
        while True:
            state = stack[-1]
            lookahead = w[cursor]
            if self.verbose: print(stack, '<---||--->', w[cursor:])
                
            # (Detect error)
            try:
              action, tag = self.action[state, lookahead][0]

              # (Shift case)
              if action == 'SHIFT':
                stack.append(tag)
                cursor += 1

              # (Reduce case)
              elif action == 'REDUCE':
                for _ in range(len(tag.Right)):
                  stack.pop()
                
                stack.append(self.goto[(stack[-1], tag.Left)][0])
                output.append(tag)

              # (OK case)
              elif action == 'OK':
                output.reverse()
                return output

              # (Invalid case)
              else:
                assert False, 'ERROR'

            except KeyError:
              return None

    def _register(self, table, key, value):
        if key not in table:
          table[key] = []
          table[key].append(value)
        else:
          if value not in table[key]:
            table[key].append(value)

        return len(table[key]) == 1

        # if key not in table or table[key] == value:
        #   table[key] = value
        #   return True
        # else:
        #   return False


class SLR1Parser(ShiftReduceParser):
    def LR0_automaton(self):
        G = self.G.AugmentedGrammar(True)
        assert len(G.startSymbol.productions) == 1, 'Grammar must be augmented'

        start_production = G.startSymbol.productions[0]
        start_item = Item(start_production, 0)

        automaton = State(start_item, True)

        pending = [ start_item ]
        visited = { start_item: automaton }

        while pending:
            current_item = pending.pop()
            if current_item.IsReduceItem:
                continue
              
            # (Decide which transitions to add)
            next_symbol = current_item.NextSymbol
            next_item = current_item.NextItem()

            if not next_item in visited:
              pending.append(next_item)
              visited[next_item] = State(next_item, True)

            if next_symbol.IsNonTerminal:
              for production in next_symbol.productions:
                next_item = Item(production, 0)
                if not next_item in visited:
                  pending.append(next_item)
                  visited[next_item] = State(next_item, True)

            current_state = visited[current_item]

            # (Add the decided transitions)
            current_state.add_transition(next_symbol.Name, visited[current_item.NextItem()])

            if next_symbol.IsNonTerminal:
              for production in next_symbol.productions:
                current_state.add_epsilon_transition(visited[Item(production, 0)])

        self.automaton = automaton.to_deterministic()
 
    def _build_parsing_table(self):
        G = self.G.AugmentedGrammar(True)
        self.isSLR1 = True
        self.LR0_automaton()

        firsts = compute_firsts(G)
        follows = compute_follows(G, firsts)

        for i, node in enumerate(self.automaton):
          if self.verbose: print(i, '\t', '\n\t '.join(str(x) for x in node.state), '\n')
          node.idx = i

        for node in self.automaton:
          idx = node.idx
          for state in node.state:
              item = state.state
              if item.IsReduceItem:
                production = item.production
                if production.Left.Name == G.startSymbol.Name:
                  self.isSLR1 &= self._register(self.action, (idx, G.EOF), ('OK', None))
                else:
                  for symbol in follows[production.Left]:
                    self.isSLR1 &= self._register(self.action, (idx, symbol), ('REDUCE', production))
              else:
                next_symbol = item.NextSymbol
                if next_symbol.IsTerminal:
                  self.isSLR1 &= self._register(self.action, (idx, next_symbol), ('SHIFT', node[next_symbol.Name][0].idx))
                else:
                  self.isSLR1 &= self._register(self.goto, (idx, next_symbol), node[next_symbol.Name][0].idx)
                      
           
class LR1Parser(ShiftReduceParser):
    def expand(self, item, firsts):
        next_symbol = item.NextSymbol
        if next_symbol is None or not next_symbol.IsNonTerminal:
            return []
        
        lookaheads = ContainerSet()
        # (Compute lookahead for child items)
        for preview in item.Preview():
            lookaheads.update(compute_local_first(firsts, preview))
          
        assert not lookaheads.contains_epsilon
        # (Build and return child items)   
        return [Item(production, 0, lookaheads) for production in next_symbol.productions]

    def compress(self, items):
      centers = {}

      for item in items:
          center = item.Center()
          try:
              lookaheads = centers[center]
          except KeyError:
              centers[center] = lookaheads = set()
          lookaheads.update(item.lookaheads)
      
      return { Item(x.production, x.pos, set(lookahead)) for x, lookahead in centers.items() }

    def closure_lr1(self, items, firsts):
        closure = ContainerSet(*items)
        
        changed = True
        while changed:
            changed = False
            
            new_items = ContainerSet()
            for item in closure:
                new_items.extend(self.expand(item, firsts))

            changed = closure.update(new_items)
            
        return self.compress(closure)

    def goto_lr1(self, items, symbol, firsts=None, just_kernel=False):
      assert just_kernel or firsts is not None, '`firsts` must be provided if `just_kernel=False`'
      items = frozenset(item.NextItem() for item in items if item.NextSymbol == symbol)
      return items if just_kernel else self.closure_lr1(items, firsts)

    def LR1_automaton(self):
      G = self.G.AugmentedGrammar(True)
      assert len(G.startSymbol.productions) == 1, 'Grammar must be augmented'

      firsts = compute_firsts(G)
      firsts[G.EOF] = ContainerSet(G.EOF)

      start_production = G.startSymbol.productions[0]
      start_item = Item(start_production, 0, lookaheads=(G.EOF,))
      start = frozenset([start_item])

      closure = self.closure_lr1(start, firsts)
      automaton = State(frozenset(closure), True)

      pending = [ start ]
      visited = { start: automaton }

      while pending:
          current = pending.pop()
          current_state = visited[current]

          for symbol in G.terminals + G.nonTerminals:
              # (Get/Build `next_state`)
              kernels = self.goto_lr1(current_state.state, symbol, just_kernel=True)

              if not kernels:
                  continue
                
              try:
                  next_state = visited[kernels]
              except KeyError:
                  pending.append(kernels)
                  visited[pending[-1]] = next_state = State(frozenset(self.goto_lr1(current_state.state, symbol, firsts)), True)

              current_state.add_transition(symbol.Name, next_state)
   
      self.automaton = automaton    

    def _build_parsing_table(self):
        G = self.G.AugmentedGrammar(True)
        self.isLR1 = True
        self.LR1_automaton()

        for i, node in enumerate(self.automaton):
            if self.verbose: print(i, '\t', '\n\t '.join(str(x) for x in node.state), '\n')
            node.idx = i

        for node in self.automaton:
            idx = node.idx
            for item in node.state:
                # - Fill `self.Action` and `self.Goto` according to `item`)
                # - Feel free to use `self._register(...)`)
                if item.IsReduceItem:
                  production = item.production
                  if production.Left.Name == G.startSymbol.Name:
                    self.isLR1 &= self._register(self.action, (idx, G.EOF), ('OK', None))
                  else:
                    for lookahead in item.lookaheads:
                      self.isLR1 &= self._register(self.action, (idx, lookahead), ('REDUCE', production))

                else:
                  next_symbol = item.NextSymbol
                  if next_symbol.IsTerminal:
                    self.isLR1 &= self._register(self.action, (idx, next_symbol), ('SHIFT', node[next_symbol.Name][0].idx))
                  else:
                    self.isLR1 &= self._register(self.goto, (idx, next_symbol), node[next_symbol.Name][0].idx)



class LALR1Parser(LR1Parser):
  def merge(self, items1, items2):
    if len(items1) != len(items2):
      return False

    lookaheads = []
    for item1 in items1:
      for item2 in items2:
        if item1.Center() == item2.Center():
          lookaheads.append(item2.lookaheads)
          break
      else:
        return False

    for item in items1:
      for lookahead in lookaheads:
        item.lookaheads = item.lookaheads.union(lookahead)
    
    return True


  def LR1_automaton(self):
    super().LR1_automaton()

    states = list(self.automaton)
    new_states = []
    visited = {}

    for i, state in enumerate(states):
      if state not in visited:
        items1 = [item.Center() for item in state.state]

        for state2 in states[i:]:
          if self.merge(items1, state2.state):
            visited[state2] = len(new_states)
        
        new_states.append(State(frozenset(items1),True))

    for state in states:
      new_state = new_states[visited[state]]
      for symbol, transitions in state.transitions.items():
        for state2 in transitions:
          new_state2 = new_states[visited[state2]]
          if symbol not in new_state.transitions or new_state2 not in new_state.transitions[symbol]:
            new_state.add_transition(symbol, new_state2)

    new_states[0].set_formatter(empty_formatter)
    self.automaton = new_states[0]


