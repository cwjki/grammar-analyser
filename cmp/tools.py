from cmp.utils import ContainerSet
from cmp.pycompiler import *
from cmp.automata import *


def compute_local_first(firsts, alpha):
    first_alpha = ContainerSet()
    
    try:
        alpha_is_epsilon = alpha.IsEpsilon
    except:
        alpha_is_epsilon = False
    
    if alpha_is_epsilon:
        first_alpha.set_epsilon()

    else:
        for symbol in alpha:
            first_symbol = firsts[symbol]
            first_alpha.update(first_symbol)
            if not first_symbol.contains_epsilon:
                break
            else:
                first_alpha.set_epsilon()
    
    return first_alpha

def compute_firsts(G):
    firsts = {}
    change = True

    for terminal in G.terminals:
        firsts[terminal] = ContainerSet(terminal)
        
    for nonterminal in G.nonTerminals:
        firsts[nonterminal] = ContainerSet()
    
    while change:
        change = False
        
        for production in G.Productions:
            X = production.Left
            alpha = production.Right

            first_X = firsts[X]
                
            try:
                first_alpha = firsts[alpha]
            except:
                first_alpha = firsts[alpha] = ContainerSet()
            
            local_first = compute_local_first(firsts, alpha)
            
            change |= first_alpha.hard_update(local_first)
            change |= first_X.hard_update(local_first)
                    
    return firsts

def compute_follows(G, firsts):
    follows = { }
    change = True
    
    local_firsts = {}

    for nonterminal in G.nonTerminals:
        follows[nonterminal] = ContainerSet()
    follows[G.startSymbol] = ContainerSet(G.EOF)
    
    while change:
        change = False
        
        for production in G.Productions:
            X = production.Left
            alpha = production.Right
            
            follow_X = follows[X]
            
            for i in range(len(alpha)):
                symbol = alpha[i]
                if symbol.IsNonTerminal:
                    follow_symbol = follows[symbol]
                    beta = alpha[i+1:]
                    
                    try:
                        first_beta = local_firsts[beta]
                    except:
                        first_beta = local_firsts[beta] = compute_local_first(firsts, beta)
            
                    change |= follow_symbol.update(first_beta)
                    if first_beta.contains_epsilon or len(beta) == 0:
                        change |= follow_symbol.update(follow_X)

    return follows

def build_parsing_table(G, firsts, follows):
    M = {}
    isLL1 = True
    conflict = None

    for production in G.Productions:
        X = production.Left
        alpha = production.Right
          
        first_alpha = firsts[alpha]
        for symbol in first_alpha:
            try:
                M[X, symbol].append(production)
                isLL1 = False
                conflict = trace_conflict(G, M, X, symbol, production, M[X, symbol][0])
                return M, isLL1, conflict
            except KeyError:
                M[X, symbol] = [production]

        if first_alpha.contains_epsilon:
            for symbol in follows[X]:
                try:
                    M[X, symbol].append(production)
                    isLL1 = False    
                    conflict = trace_conflict(G, M, X, symbol, production, M[X, symbol][0]) 
                    return M, isLL1, conflict            
                except KeyError:
                    M[X, symbol] = [production]
                    
    return M, isLL1, conflict            

def metodo_predictivo_no_recursivo(G, M):
    def parser(w):
        stack =  [G.startSymbol]
        cursor = 0
        output = []

        while True:
            top = stack.pop()
            a = w[cursor]
            
            if top.IsTerminal:
                if top == a:
                    cursor += 1
                else:
                    print("Esta mal.")
                    return None
            else:
                production = M[top,a][0]
                output.append(production)
                alpha = production.Right
                for i in range(len(alpha)):
                    stack.append(alpha[-i-1])  
            
            if len(stack) == 0:
                break

        # left parse is ready!!!
        return output
    
    # parser is ready!!!
    return parser
       

def trace_conflict(G, M, X, term, p1, p2):
    stack = [p1]
    resp = p1.Right.expand(term = term, marked = {})
    while True:
        elem = stack.pop()
        if elem.Left == G.startSymbol:
            break
        for key in M:
            brake = False
            item = M[key][0].Right
            for i, e in enumerate(item):
                if elem.Left == e:
                    idx = i
                    resp = Sentence(*item[:idx]).expand(marked = {}, term = key[1]) + resp + Sentence(*item[idx+1:]).expand(marked = {})
                    stack.append(M[key][0])
                    brake = True
                    break
            if brake:
                break
    
    return (resp, repr(p1), repr(p2))

class DerivationTree:
    def __init__(self, symbol):
        self.symbol = symbol
        self.childrens = []

    @staticmethod      
    def do_the_tree(parser, count, parserType):
        production = parser[count]
        tree = DerivationTree(production.Left)
        current = count + 1

        if parserType == "left":
            production_right = production.Right
        else:
            production_right = reversed(production.Right)

        for symbol in production_right:
            if symbol.IsTerminal:
                tree.childrens.append(DerivationTree(symbol))
            else:
                ctree, current = DerivationTree.do_the_tree(parser, current, parserType)
                tree.childrens.append(ctree)

        if parserType == "right": tree.childrens.reverse()       
        return tree, current

    def __str__(self, level=0):
        ret = "|..."*level+repr(self.symbol)+"\n"
        for child in self.childrens:
            ret += child.__str__(level+1)
        return ret



def without_left_recursion(grammar):
    G_prima = grammar.copy()
    for nt in G_prima.nonTerminals:
        changed = False
        stack = []
        nt_prima = nt.Name + '_prima'
        for p in nt.productions:
            if not p.IsEpsilon and p.Right[0] == nt:
                if not changed:
                     #agregar el nuevo nt a la nueva gramatica
                    G_prima.NonTerminal(nt_prima)
                    
                #agregar la nueva produccion a la gramatica
                nt_prima = G_prima.nonTerminals[-1]

                if not changed:
                    #agregar que nt se va en epsilon
                    G_prima.Add_Production(Production(nt_prima, G_prima.Epsilon))
                    changed = True

                G_prima.Add_Production(Production(nt_prima, Sentence(*p.Right[1:], nt_prima)))
                
                #quitar a la produccion de la recursion
                G_prima.Productions.remove(p)
            else:
                stack.append(p)

        if changed:
            nt.productions = []

        while changed and len(stack):
            p = stack.pop()
            if p.IsEpsilon:
                G_prima.Add_Production(Production(nt, nt_prima))
            else:
                s = Sentence(*p.Right, nt_prima)
                G_prima.Productions.remove(p)
                G_prima.Add_Production(Production(nt, s))

    return G_prima

def without_common_prefix(grammar):
    G = grammar.copy()
    nts = G.nonTerminals.copy()
    new_nts = []
    new_prods = []
    old_prods = []
    while len(nts):
        nt = nts.pop()
        changed = False
        comunes = []
        for p in nt.productions:
            if p in old_prods:
                continue
            if p.IsEpsilon:
                if p not in new_prods:
                    new_prods.append(p)
                continue
            comunes.append(p)
            copy = nt.productions.copy()
            copy.reverse()
            for p2 in copy:
                if p2 == p:
                    break
                if not p2.IsEpsilon and p2.Right[0] == p.Right[0]:
                    old_prods.append(p2)
                    old_prods.append(p)
                    comunes.append(p2)
                    changed = True
            if changed:
                nts.append(NonTerminal(nt.Name + '_prima', G))
                nt_prima = nts[-1]
                new_prods.append(Production(nt, Sentence(p.Right[0], nt_prima)))
                new_nts.append(nt_prima)
                for c in comunes:
                    if len(c.Right) == 1:
                        new_prods.append(Production(nt_prima, G.Epsilon))
                        nt_prima.productions.append(Production(nt_prima, G.Epsilon))
                    else:
                        new_prods.append(Production(nt_prima, Sentence(*c.Right[1:])))
                        nt_prima.productions.append(Production(nt_prima, Sentence(*c.Right[1:])))
                changed = False
            else:
                if comunes[0] not in new_prods:
                    new_prods.append(comunes[0])
            comunes = []

    G.nonTerminals += new_nts
    G.Productions = new_prods
    return G


def without_unitary_productions(grammar, empty_word):
    G = grammar.copy()
    H = {}
    P = []
    change = True

    for nt in G.nonTerminals:
        for p in nt.productions:
            if len(p.Right) == 1 and p.Right[0].IsNonTerminal and p.Right[0] != nt:
                try:
                    H[nt].append(p.Right[0])
                except:
                    H[nt] = [p.Right[0]]
            else:
                P.append(Production(nt, p.Right))
                    
    while change:
        change = False
        for item in H:
            for v in H[item]:
                try:
                    for v2 in H[v]:
                        if v2 != item and v2 not in H[item]:
                            H[item].append(v2)
                            change = True
                except:
                    continue
                    
    for nt in G.nonTerminals:
        for item in H:
            if item == nt:
                continue
            else:
                if nt in H[item]:
                    for p in nt.productions:
                        if not(len(p.Right)==1 and p.Right[0].IsNonTerminal) and Production(item, p.Right) not in P:
                            P.append(Production(item, p.Right))
    
    G_prima = G.copy()
    G_prima.Productions = P

    if empty_word:
        new_start = G_prima.startSymbol.Name + '_prima'
        G_prima.NonTerminal(new_start, True)
        G_prima.Add_Production(Production(G_prima.startSymbol, G.Epsilon))
        G_prima.Add_Production(Production(G_prima.startSymbol, G.startSymbol))

    return G_prima

def without_useless_symbols(grammar):
    G = grammar.copy()

    #Quitar los simbolos que no generen una palabra del vocabulario de los terminales
    M = []
    change = True
    for p in G.Productions:
        if all(symbol in G.terminals for symbol in p.Right) and p.Left not in M:
            M.append(p.Left)
    while change:
        change = False
        for p in G.Productions:
            if all(symbol in M for symbol in p.Right if symbol.IsNonTerminal) and p.Left not in M:
                M.append(p.Left)
                change = True

    if len(M) != len(G.nonTerminals):
        productions_prima = []
        t_prima = []
        for nt in G.nonTerminals:
            if nt in M:
                nt_productions = []
                for p in nt.productions:
                    if all(symbol in M for symbol in p.Right if symbol.IsNonTerminal):
                        nt_productions.append(p)
                        productions_prima.append(p)
                        for t in p.Right:
                            if t not in t_prima and t.IsTerminal:
                                t_prima.append(t)
                nt.productions = nt_productions
        G_prima = G.copy()
        G_prima.Productions = productions_prima
        G_prima.nonTerminals = M
        G_prima.terminals = t_prima
    else:
        G_prima = G.copy()


    #Quitar los simbolos inalcanzables desde S
    pending = [G_prima.startSymbol]
    V = [G_prima.startSymbol]

    while len(pending):
        a = pending.pop()
        for p in a.productions:
            for symbol in p.Right:
                if symbol not in V:
                    V.append(symbol)
                    if symbol.IsNonTerminal:
                        pending.append(symbol)

    terminals_prima = [terminal for terminal in G_prima.terminals if terminal in V]
    nonterminals_prima = [nonterminal for nonterminal in G_prima.nonTerminals if nonterminal in V]
    productions_prima = []
    
    for nt in nonterminals_prima:
        nt_productions = []
        for elem in G_prima.nonTerminals:
            if elem == nt:
                for p in elem.productions:
                    if all(symbol in V for symbol in p.Right):
                        nt_productions.append(p)
                        productions_prima.append(p)
        nt.productions = nt_productions

    G_prima_prima = G.copy()
    G_prima_prima.Productions = productions_prima
    G_prima_prima.terminals = terminals_prima
    G_prima_prima.nonTerminals = nonterminals_prima

    return G_prima_prima

def without_epsilon_transitions(grammar):
    G = grammar.copy()
    H = []
    empty_word = False
    productions_prima = []
    final_productions = []
    other_productions = []
    prods = {}
    change = True
    for p in G.Productions:
        if p.IsEpsilon:
            H.append(p.Left)
        else:
            productions_prima.append(p)
    while change:
        change = False
        for p in G.Productions:
            if all(symbol in H for symbol in p.Right) and p.Left not in H:
                H.append(p.Left)
                change = True
    
    if not len(H):
        return grammar, empty_word

    for p in productions_prima:
        check = False
        for i, symbol in enumerate(p.Right):
            if symbol in H:
                try:
                    prods[p].append(i)
                except:
                    prods[p] = [i]
                    check = True
        if not check:
            other_productions.append(p)

    nt_ready = []
    for p in prods:
        cp = pot(len(prods[p]))
        p_new_productions = genera(p, prods, cp)
        for elem in p_new_productions:
            final_productions.append(elem)
        if p.Left not in nt_ready:
            nt_ready.append(p.Left)
            p.Left.productions = p_new_productions
        else:
            for nt in nt_ready:
                if nt == p.Left:
                    for elem in p_new_productions:
                        nt.productions.append(elem)
                    break
    
    for p in other_productions:
        # final_productions.append(p)
        # head = p.Left
        # if p not in head.productions:
        #     head.productions.append(p)
        # if head not in nt_ready:
        #     nt_ready.append(head)
        head = p.Left
        if head not in nt_ready:
            head.productions = []
            nt_ready.append(head)
        head.productions.append(p)
        final_productions.append(p)

    G_prima = G.copy()
    G_prima.Productions = final_productions
    G_prima.nonTerminals = nt_ready

    if G.startSymbol in H:
        empty_word = True
        
    return G_prima, empty_word

def pot(i):
    if i == 1:
        resp = [[0], [1]]
        return resp
    resp = []
    cp = pot(i-1)
    for item in cp:
        resp.append(item + [0])
        resp.append(item + [1])
    return resp

def genera(p, prods, cp):
    final_productions = []

    for c in cp:
        last = 0
        new_p = []
        count = 0
        for i, symbol in enumerate(c):
            if symbol:
                count+=1
                while last < prods[p][i]:
                    new_p.append(p.Right[last])
                    last+=1
                last = prods[p][i] + 1
        while last < len(p.Right):
                new_p.append(p.Right[last])
                last+=1

        if not (count == len(c) == len(p.Right)):
            final_productions.append(Production(p.Left, Sentence(*new_p)))

    return final_productions



def regex_from_dfa(dfa):
    in_transitions = dfa.in_transitions
    out_transitions = dfa.out_transitions
    stack = [dfa.start]
    regex = ''

    while len(stack):
      elem = stack.pop()
      cycle = False
      aster = ''

      if elem == dfa.start:
        for i in out_transitions[elem]:
            if i not in dfa.finals and i not in stack:
                stack.append(i)
      else:
        for t in in_transitions[elem]:
            if t != elem:
                for t2 in out_transitions[elem]:
                    symbol = in_transitions[elem][t]
                    if t2 != elem:
                        if t2 not in stack and t2 not in dfa.finals and t2 != dfa.start:
                            stack.append(t2)
                            
                        if elem in in_transitions[elem]:
                            aster = '(' + in_transitions[elem][elem] + ')' + '*'
                        symbol += aster + out_transitions[elem][t2]

                        try:
                            out_transitions[t][t2] = '(' + out_transitions[t][t2] + ') | (' + symbol + ')'
                        except:
                            out_transitions[t][t2] = symbol
                        try:
                            in_transitions[t2][t] = '(' + in_transitions[t2][t] + ') | (' + symbol + ')'
                        except:
                            in_transitions[t2][t] = symbol

                del out_transitions[t][elem]

        for item in out_transitions[elem]:
            del in_transitions[item][elem]
        del out_transitions[elem]
        del in_transitions[elem]
        dfa.states -= 1

    new_indexs = {}
    if len(dfa.finals) > 1:
      final_regexs = []
      final_states_copy = dfa.finals
      for final_state in final_states_copy:
            if new_indexs == {}:
                new_indexs = convert_indexs(dfa)
            copia = dfa.copy(new_indexs)
            final_regexs.append(final_exp(copia, new_indexs[final_state]))
      for item in final_regexs:
        if item != '':
            if regex == '':
                regex = '(' + item + ')'
            else:
                regex += ' | (' + item + ')'

    else:
        cycle = ''
        final_state = dfa.finals.pop()
        if final_state in in_transitions[final_state]:
            cycle = '(' + in_transitions[final_state][final_state] + ')' + '*'

        for i in in_transitions[final_state]:
            if i != final_state:
                if regex == '':
                    regex = in_transitions[final_state][i] + cycle
                else:
                    regex = '(' + regex + ') | ( ' + in_transitions[final_state][i] + cycle + ')'


    return regex

def final_exp(dfa, final_state):
   dfa.finals = [final_state]
   return regex_from_dfa(dfa)


