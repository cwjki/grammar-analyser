from flask import Flask, render_template, url_for, request, redirect
from cmp.grammarAnalyzer import GrammarAnalyser, BadGrammarException


app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def index():
    try:
        if request.method == 'POST':
            grammar = request.form['grammar']
            words = request.form['words']

            if grammar == '':
                return redirect('/')

            analyser = GrammarAnalyser(grammar)
            analyser.tokenizer(words)
            analyser.computeFirst()
            analyser.computeFollow()
         
            analyser.LL1()
            analyser.SLR1()
            analyser.LR1()
            analyser.LALR1()
            
            parser = None
            if analyser.isLL1:
                parser = analyser.LL1Parser
            if analyser.SLR1:
                parser = analyser.SLR1Parser
            if analyser.isLR1:
                parser = analyser.LR1Parser
            if analyser.isLALR1:
                parser = analyser.LALR1Parser

            if parser:
                if analyser.words:
                    analyser.getParserType()
                    analyser.getDerivations(parser)
                    analyser.doTheTree()
                    analyser.derivationsLen = len(analyser.derivations)

            
            if analyser.IsRegular():
                analyser.RegularAutomata()
                analyser.regexFromDfa()

            analyser.withoutLeftRecursion()
            analyser.withoutCommonPrefix()
            analyser.almostFNCh()

        
            return render_template('result.html', analyser = analyser)

        else:
            return render_template('index.html', boolean=False )

    except BadGrammarException:
        return render_template('index.html', boolean= True)




if __name__ == "__main__":
    app.run()