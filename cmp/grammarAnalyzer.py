import json
from cmp.pycompiler import Grammar, Terminal, NonTerminal
from cmp.tools import *
from cmp.shiftReduceParsers import SLR1Parser, LR1Parser, LALR1Parser
from cmp.automata import NFA, nfa_to_dfa

class BadGrammarException(Exception):
  pass

class GrammarAnalyser():

  def __init__(self, grammarText: str):
    self.G = self.parseGrammar(grammarText)
    self.firsts = None
    self.follows = None
    # LL1
    self.LL1Table = None
    self.LL1Parser = None
    self.isLL1 = None
    # SLR1
    self.SLR1Parser = None
    self.isSLR1 = None
    # LR1
    self.LR1Parser = None
    self.isLR1 = None
    # LALR1
    self.LALR1Parser = None
    self.isLALR1 = None

    self.grammmar_without_left_recursion = None
    self.grammar_without_common_prefix = None
    self.almost_FNCh = None

    self.isRegular = None
    self.NFA = None
    self.DFA = None

    self.words = []
    self.parserType = None
    self.derivations = []
    self.derivationTree = []
    self.derivationsLen = 0

    self.LL1_conflict = None

  def parseGrammar(self, text: str):
    terminals, nonTerminals, productions = [], [], []

    try:
        lines = text.split('\r\n')

        for line in lines:
          head, bodies = line.split('->')
          head, = head.split()

          if len(head[0]) > 1:
            raise BadGrammarException()

          nonTerminals.append(head)

          for body in bodies.split('|'):
            productions.append({'Head': head, 'Body': list(body.split())})
            terminals.extend(productions[-1]['Body'])
    
    except:
      raise BadGrammarException()

    nonTerminals = set(nonTerminals)
    terminals = set([t for t in terminals if t not in nonTerminals and t != 'epsilon'])

    data = json.dumps({
                        'NonTerminals' : [nt for nt in nonTerminals],
                        'Terminals' : [t for t in terminals],
                        'Productions' : productions
    })

    return Grammar.from_json(data)
    
  def computeFirst(self):
    self.firsts = compute_firsts(self.G)

  def computeFollow(self):
    self.follows = compute_follows(self.G, self.firsts)

  def tokenizer(self, text):
    if text == '':
      self.words = None
      return

    words = text.split('\r\n')
    
    for word in words:
      discard = False
      aux = []

      for w in word.split(' '):   
        if (self.G[w] is None):
          self.words.append((word, False))
          discard = True
          break
        else:
          aux.append(self.G[w]) 

      if not discard:
        aux.append(self.G.EOF)
        self.words.append((aux, True))

  def LL1(self):
    self.LL1Table, self.isLL1, self.LL1_conflict = build_parsing_table(self.G, self.firsts, self.follows)
    self.LL1Parser = metodo_predictivo_no_recursivo(self.G, self.LL1Table)

  def SLR1(self):
    self.SLR1Parser = SLR1Parser(self.G)
    self.isSLR1 = self.SLR1Parser.isSLR1
    if self.isSLR1:
      self.SLR1Parser.automaton.write_to("static/images/automatonLR0.svg")

  def LR1(self):
    self.LR1Parser = LR1Parser(self.G)
    self.isLR1 = self.LR1Parser.isLR1
    if self.isLR1:
      self.LR1Parser.automaton.write_to("static/images/automatonLR1.svg")

  def LALR1(self):
    self.LALR1Parser = LALR1Parser(self.G)
    if self.isLR1:
      self.LALR1Parser.automaton.write_to("static/images/automatonLALR1.svg")

  def IsRegular(self):
    startSymbol = False
    epsilon = False

    for production in self.G.Productions:
      if len(production.Right) > 2:
        self.isRegular = False
        return False

      if production.Right.IsEpsilon:
        if production.Left != self.G.startSymbol:
          self.isRegular = False
          return False
        else:
          epsilon = True
          continue

      if not production.Right[0].IsTerminal:
        self.isRegular = False
        return False
      
      if len(production.Right) == 2:
        if production.Right[1].IsTerminal:
          self.isRegular = False
          return False

      for symbol in production.Right:
        if symbol == self.G.startSymbol:
          startSymbol = True

    self.isRegular = not (epsilon and startSymbol)
    return self.isRegular

  def RegularAutomata(self):
    finals = []
    transitions = {}
    states = {}
    tags = {}

    startSymbol = self.G.startSymbol
    states[startSymbol.Name] = 0
    tags[0] = startSymbol.Name

    idx = 1
    nonTerminals = self.G.nonTerminals.copy()
    while nonTerminals:
      state = nonTerminals.pop()
      if state.Name != startSymbol.Name:
        states[state.Name] = idx
        tags[idx] = state.Name
        idx += 1
      
    # for idx, nt in enumerate(self.G.nonTerminals):
    #   states[nt.Name] = idx
    #   tags[idx] = nt.Name
    
    for production in self.G.Productions:
      head = production.Left
      body = production.Right

      if body.IsEpsilon:
        finals.append(states[head.Name])

      elif len(body) == 2:
        try:
          transitions[states[head.Name], body[0].Name].append(states[body[1].Name])
        except:
          transitions[states[head.Name], body[0].Name] = [states[body[1].Name]]

      elif len(body) == 1:
        try:
          transitions[states[head.Name], body[0].Name].append(len(states))
        except:
          transitions[states[head.Name], body[0].Name] = [len(states)]

        if len(states) not in finals:
          finals.append(len(states))

      else:
        raise Exception('ERROR en RegularAutomata')

    if len(states) in finals:
      tags[len(states)] = '_Z_'

    self.NFA = NFA(len(self.G.nonTerminals) + int(len(states) in finals), finals, transitions)
    self.DFA = nfa_to_dfa(self.NFA)
    self.DFA.write_to("static/images/regularAutomaton.svg")
  
  def regexFromDfa(self):
    self.regex = regex_from_dfa(self.DFA)

  
  def getParserType(self):
    if self.isSLR1 or self.isLR1 or self.isLALR1:
      self.parserType = "right"

    elif self.isLL1:
      self.parserType = "left"


  def getDerivations(self, parser):
    for word, boolean in self.words:
        if boolean:
            self.derivations.append(parser(word))
        else:
             self.derivations.append(None)
  
  def doTheTree(self):
    for d in self.derivations:
      if d:
        d = DerivationTree.do_the_tree(d, 0, self.parserType)[0]
        self.derivationTree.append(d.__str__())
      else:
       self.derivationTree.append("La gramática no reconoce esta cadena.") 
   


  def withoutLeftRecursion(self):
    self.grammmar_without_left_recursion = without_left_recursion(self.G)

  def withoutCommonPrefix(self):
    self.grammar_without_common_prefix = without_common_prefix(self.grammmar_without_left_recursion)  


  def almostFNCh(self):
    grammar = self.grammar_without_common_prefix
    grammar = without_useless_symbols(grammar)
    grammar, empty_word = without_epsilon_transitions(grammar)
    grammar = without_unitary_productions(grammar, empty_word)
    self.almost_FNCh = grammar

  
  
    











