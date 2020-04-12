import pydot
from grammarAnalizer import GrammarAnalyser


grammarText = 'E -> T X \r\n X -> + T X | - T X | epsilon \r\n T -> F Y \r\n Y -> * F Y | / F Y | epsilon \r\n F -> ( E ) | i'
text = 'i + i - i \n i*i+i\ni+(i*i)\ni+4*i\ni*i*i+i*i+i+i'

analyser = GrammarAnalyser(grammarText)
analyser.computeFirst()
analyser.computeFollow()
analyser.LL1()
#analyser.tokenizer(text)
analyser.SLR1()


analyser.LR1()
analyser.LALR1()

for word in analyser.words:
  w, boolean = word
  if boolean is None:
    leftparse = analyser.LL1Parser(w)



print('Finish')