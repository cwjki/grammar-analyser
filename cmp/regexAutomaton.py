
class Regex:
    def __init__(self):
        pass

    def evaluate(self):
        raise NotImplementedError()

    def simplify(self):
        raise NotImplementedError()

    def __repr__(self):
        return str(self)
    
    def __eq__(self,other):
        if isinstance(other,type(self)):
            return str(self) == str(other)
        return False

    def copy(self):
        raise NotImplementedError()

class AtomicNode(Regex):
    
    def __init__(self,symbol):
        self.text = symbol

    def __str__(self):
        return self.text

    def evaluate(self):
        return self
    
    def copy(self):
        return AtomicNode(self.text)

class EpsilonNode(Regex):
    
    def __init__(self):
        self.text = 'ε'

    def __str__(self):
        return self.text

    def evaluate(self):
        return self

    def copy(self):
        return EpsilonNode()

class UnionNode(Regex):
    
    def __init__(self,childs=[]):
        self.childs = []
        for child in childs:
            if not child in self.childs:
                self.childs.append(child)

    def __str__(self):
        result = []
        for child in self.childs:
            result.append(str(child))
        c = ' | '
        return f'({c.join(result)})'
    
    def __eq__(self,other):
        if not isinstance(other,type(self)) or len(self.childs) != len(other.childs):
            return False
        for child in other.childs:
            if not child in self.childs:
                return False
        return True

    def simplify(self):
        if len(self.childs) == 0:
            return EmptyNode()
        if len(self.childs) == 1:
            return self.childs[0]
        childs = []
        for child in self.childs:
            if not isinstance(child,EmptyNode) and not child in childs:
                childs.append(child)
        self.childs = childs
        if len(self.childs) == 1:
            return self.childs[0]
        return self
    
    def removeEpsilon(self):
        childs = []
        for child in self.childs:
            if not isinstance(child,EpsilonNode):
                childs.append(child)
        self.childs = childs
        if len(self.childs) == 1:
            return self.childs[0]
        return self

    def evaluate(self):
        for i in range(len(self.childs)):
            self.childs[i] = self.childs[i].evaluate()
        return self.simplify()
    
    def copy(self):
        return UnionNode([c.copy() for c in self.childs])

class ConcatNode(Regex):
    
    def __init__(self,childs=[]):
        self.childs = childs

    def __str__(self):
        result = []
        for child in self.childs:
            result.append(str(child))
        c = ' '
        return f'({c.join(result)})'
    
    def __eq__(self,other):
        if not isinstance(other,type(self)) or len(self.childs) != len(other.childs):
            return False
        for i in range(len(self.childs)):
            if self.childs[i] != other.childs[i]:
                return False
        return True

    def simplify(self):
        if len(self.childs) == 1:
            return self.childs[0]
        childs = []
        for child in self.childs:
            if isinstance(child,EmptyNode):
                return EmptyNode()
            if not isinstance(child,EpsilonNode):
                childs.append(child)
        self.childs = childs
        return self

    def evaluate(self):
        for i in range(len(self.childs)):
            self.childs[i] = self.childs[i].evaluate()
        childs = []
        for child in self.childs:
            if isinstance(child,ConcatNode):
                for c in child.childs:
                    childs.append(c)
            else:
                childs.append(child)
        self.childs = childs
        return self.simplify()
    
    def copy(self):
        return ConcatNode([c.copy() for c in self.childs])

class ClousureNode(Regex):
    
    def __init__(self,child):
        self.child = child

    def __str__(self):
        if isinstance(self.child,UnionNode):
            return f'{str(self.child)}*'
        return f'({str(self.child)})*'
    
    def __eq__(self,other):
        if not isinstance(other,type(self)):
            return False
        return self.child == other.child

    def simplify(self):
        if isinstance(self.child,UnionNode):
            self.child = self.child.removeEpsilon()
        if isinstance(self.child,EpsilonNode):
            return self.child
        return self
    
    def evaluate(self):
        self.child = self.child.evaluate()
        return self.simplify()
    
    def copy(self):
        return ClousureNode(self.child.copy())

class EmptyNode(Regex):
    
    def __init__(self):
        self.text = '@'

    def __str__(self):
        return self.text

    def evaluate(self):
        return self
    
    def copy(self):
        return EmptyNode()




