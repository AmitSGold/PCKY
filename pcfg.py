import copy
from ptree import PTree, Node



class PRule(object):
    def __init__(self, variable, derivation, probability):
        self.variable = str(variable)
        self.derivation = tuple(derivation)
        self.probability = float(probability)

    def derivation_length(self):
        return len(self.derivation)

    def __repr__(self):
        compact_derivation = " ".join(self.derivation)
        return self.variable + ' -> ' + compact_derivation + ' (' + str(self.probability) + ')'

    def __eq__(self, other):
        try:
            return self.variable == other.variable and self.derivation == other.derivation
        except Exception:
            return False
    
    def __hash__(self):
        return hash(repr(self))


class PCFG(object):
    def __init__(self, start_variable='S', rules = None):
        if rules is None:
            self.rules = {}
        else:
            self.rules = copy.deepcopy(rules)  # A dictionary that maps an str object to a list of PRule objects
        self.start = start_variable  # Start symbol of the grammar
        self.V_size = 0
        for variable in rules:
            for rule in rules[variable]:
                self.V_size += 1
        self.changes = {}

    def add_rule(self, rule):
        """
        Adds a rule to dictionary of rules in grammar.
        """
        if rule.variable not in self.rules:
            self.rules[rule.variable] = []
        self.rules[rule.variable].append(rule)

    def remove_rule(self, rule):
        """
        Removes a rule from dictionary of rules in grammar.
        """
        try:
            self.rules[rule.variable].remove(rule)
        except KeyError:
            pass
        except ValueError:
            pass

    def to_near_cnf(self):
        """
        Returns an equivalent near-CNF grammar.
        """
        
        cnf = PCFG(self.start, self.rules)
        start_rule = PRule('S0', self.start, 1)
        cnf.start = 'S0' 
        cnf.add_rule(start_rule)
        var_gen = cnf.variable_generator()

        
        rules_d = {}
        while (cnf.rules != rules_d): #convert long rules
            rules_d = copy.deepcopy(cnf.rules)
            for variable in rules_d:
                for rule in rules_d[variable]:
                    if rule.derivation_length() > 2: 
                        cnf.convert_long_rules(rule, var_gen)
        
        rules_d = {}
        while (cnf.rules != rules_d): #convert mixed rules
            rules_d = copy.deepcopy(cnf.rules)
            for variable in rules_d:
                for rule in rules_d[variable]:
                    if rule.derivation_length() == 2:
                        if rule.derivation[0] not in rules_d\
                            or rule.derivation[1] not in rules_d:
                                cnf.convert_mixed_rules(rule, var_gen)
        
        rules_d = {}                    
        while (cnf.rules != rules_d): #eliminate epsilon rules
            rules_d = copy.deepcopy(cnf.rules)
            for variable in rules_d:
                for rule in rules_d[variable]:
                    if variable!= cnf.start and rule.derivation == ('',):
                        cnf.eliminate_e_rule(rule, rules_d)
                        

        return cnf

    def cky_parser(self, string):
        """
        Parses the input string given the grammar, using the probabilistic CKY algorithm.
        If the string has been generated by the grammar - returns a most likely parse tree for the input string.
        Otherwise - returns None.
        The CFG is given in near-CNF.
        """
        words = string.split() #split the sentce to words for easier parsing
        n = len(words)
        cky_table = [[{} for _ in range(n + 1)] for _ in range(n+1)]
        backpointers = [[{} for _ in range(n + 1)] for _ in range(n+1)]
        
        for j in range(1, n + 1):
            for variable in self.rules:
                for rule in self.rules[variable]:
                    if (words[j-1]) == rule.derivation[0]: #if the word is the rule's derivation
                        cky_table[j-1][j][rule.variable] = rule.probability
                        backpointers[j-1][j][rule.variable] = Node(variable, [words[j-1]]) #create an appropriate node
            
                for _ in range(self.V_size**2): 
                    for variable in self.rules:
                            for rule in self.rules[variable]: 
                                if rule.derivation_length() == 1:
                                    new_prob = rule.probability * get_from_dic_or_default(cky_table[j-1][j], rule.derivation[0])
                                    if get_from_dic_or_default(cky_table[j-1][j], rule.variable) < new_prob:
                                        cky_table[j-1][j][rule.variable] = new_prob
                                        backpointers[j-1][j][rule.variable] = (Node(variable, [backpointers[j-1][j][rule.derivation[0]]]))

            
            for i in range(j-2, -1, -1):
                for k in range(i+1, j):
                    for variable in self.rules:
                        for rule in self.rules[variable]:
                            if rule.derivation_length() == 2: #make sure we're not checking terminal rule
                                new_prob = rule.probability * get_from_dic_or_default(cky_table[i][k], rule.derivation[0]) \
                                                            * get_from_dic_or_default(cky_table[k][j], rule.derivation[1])
                                if get_from_dic_or_default(cky_table[i][j], rule.variable) < new_prob:
                                    cky_table[i][j][rule.variable] = new_prob
                                    backpointers[i][j][rule.variable] = Node(variable, [backpointers[i][k][rule.derivation[0]], backpointers[k][j][rule.derivation[1]]])
                                    #create a node with children as the corresponding nodes to rule's derivation

                for _ in range(self.V_size**2): 
                    for variable in self.rules:
                            for rule in self.rules[variable]: 
                                if rule.derivation_length() == 1:
                                    new_prob = rule.probability * get_from_dic_or_default(cky_table[i][j], rule.derivation[0])
                                    if get_from_dic_or_default(cky_table[i][j], rule.variable) < new_prob:
                                        cky_table[i][j][rule.variable] = new_prob
                                        backpointers[i][j][rule.variable] = (Node(variable, [backpointers[i][j][rule.derivation[0]]]))
                                               
        for row in cky_table:
            print(row)
        if get_from_dic_or_default(cky_table[0][-1], self.start) > 2**(-50):
            return PTree(backpointers[0][-1][self.start], cky_table[0][-1][self.start]) #if the start variable is in the top, generate a tree from it's node
        return None

    def is_valid_grammar(self):
        """
        Validates that the grammar is legal (meaning - the probabilities of the rules for each variable sum to 1).
        """
        for variable in self.rules:
            prob_sum = 0
            for rule in self.rules[variable]:
                prob_sum += rule.probability
            if not 0.9999 <= prob_sum <= 1.0001:
                return False
        
        return True
    
    def adjust_near_cnf_ptree(self, ptree, changes):
        """
        THIS METHOD IS RELEVANT ONLY FOR THE BONUS QUSETION.
        Adjusts a PTree derived by a grammar converted to near-CNF, to the equivalent PTree of the original grammar.
        """

        return self.adjust_near_cnf_ptree_rec(PTree(ptree.root.children[0], ptree.probability), changes)
    
    def adjust_near_cnf_ptree_rec(self, ptree, changes):
        """
        THIS METHOD IS RELEVANT ONLY FOR THE BONUS QUSETION.
        Adjusts a PTree derived by a grammar converted to near-CNF, to the equivalent PTree of the original grammar.
        """
        node = ptree.root
        
        if not isinstance(node, str):
            
            if len(node.children) > 0:
                for child in node.children:
                    if not isinstance(child, str) and child.key in changes:
                        if changes[child.key].change_type ==  'auxiliary':
                            
                            if len(node.children)>1 and node.children[1].key == changes[child.key].rule.variable:
                                node.children = node.children[:1] + node.children[1].children
                            else:
                                if node.children[0].key == child.key:
                                    node.children = node.children[0].children + node.children[1:]
                                if node.children[1].key == child.key:
                                    node.children = node.children[:1] + node.children[1].children
                    self.adjust_near_cnf_ptree_rec(PTree(child), changes)
        
        return PTree(node, ptree.probability)
    
    def eliminate_e_rule(self, rule, d):
        self.remove_and_normalize_e_rule(rule, d)
        self.adjust_e_rule_rhs(rule, d)
    
    def remove_and_normalize_e_rule(self, rule, d):
        self.remove_rule(rule)
        for r in self.rules[rule.variable]:
            r.probability = r.probability / (1-rule.probability)

    def adjust_e_rule_rhs(self, rule, d):
        A = rule.variable
        for B in d:
            for Brule in self.rules[B]:
                if A in Brule.derivation:
                    if Brule.derivation_length() > 1: #derivation length = 2
                        if A == Brule.derivation[0] and A == Brule.derivation[1]:
                            exists = False
                            for B_e_rule in self.rules[B]: #if the rule already exists, update prob
                                if B_e_rule.derivation == ('',):
                                    B_e_rule.probability += Brule.probability \
                                             * rule.probability**(2)
                                    exists = True
                                    break
                            
                            if not exists: #if its a new rule, add it
                                new_rule = PRule(Brule.variable, ('',), Brule.probability \
                                             * rule.probability**(2))
                                self.add_rule(new_rule)
                              
                            exists = False
                            for B_1_rule in self.rules[B]:
                                if B_1_rule.derivation == (A,):
                                    B_1_rule.probability += 2 * Brule.probability \
                                             * rule.probability * (1 - rule.probability)
                                    exists = True
                                    break
                            
                            if not exists:
                                new_1_rule = PRule(Brule.variable, [A], 2 * Brule.probability \
                                             * rule.probability * (1 - rule.probability))
                                self.add_rule(new_1_rule)
                               
                            Brule.probability *= (1 - rule.probability)**2                            
                        
                        elif A == Brule.derivation[0]:
                            exists = False
                            for B_1_rule in self.rules[B]:
                                if B_1_rule.derivation == (Brule.derivation[1],):
                                    B_1_rule.probability += Brule.probability \
                                             * rule.probability
                                    exists = True
                                    break
                            
                            if not exists:
                                new_rule = PRule(Brule.variable, Brule.derivation[1:], Brule.probability \
                                             * rule.probability)
                                self.add_rule(new_rule)
                                
                            Brule.probability *= (1 - rule.probability)
                        
                        elif A == Brule.derivation[1]:
                            
                            exists = False
                            for B_1_rule in self.rules[B]:
                                if B_1_rule.derivation == (Brule.derivation[0],):
                                    B_1_rule.probability += Brule.probability * rule.probability \
                                        
                                    exists = True
                                    break
                            
                            if not exists:
                                new_rule = PRule(Brule.variable, Brule.derivation[0:1], Brule.probability \
                                             * rule.probability)
                                self.add_rule(new_rule)
                        
                            Brule.probability *= (1 - rule.probability)
                            
                    elif Brule.derivation_length() == 1:
                        exists = False
                        for B_e_rule in self.rules[B]:
                            if B_e_rule.derivation == ('',):
                                B_e_rule.probability += Brule.probability \
                                             * rule.probability
                                exists = True
                                break
                            
                        if not exists:
                            new_rule = PRule(Brule.variable, ('',), Brule.probability \
                                             * rule.probability)
                            self.add_rule(new_rule)
                        
                        Brule.probability *= (1 - rule.probability)

    def convert_mixed_rules(self, rule, gen):
        der = [d for d in rule.derivation]
        
        if rule.derivation[0] not in self.rules: #if the first child is a terminal
            new_l_var = next(gen)
            der[0] = new_l_var
            new_l_rule = PRule(new_l_var, [rule.derivation[0]], 1)
            self.add_rule(new_l_rule)
            self.changes[new_l_var] = PCFGChange(new_l_rule,'auxiliary')
        
        if rule.derivation[1] not in self.rules: #if the second child is a terminal
            new_r_var = next(gen)
            der[1] = new_r_var
            new_r_rule = PRule(new_r_var, [rule.derivation[1]], 1)
            self.add_rule(new_r_rule)
            self.changes[new_r_var] = PCFGChange(new_r_rule,'auxiliary')
            
            
        new_rule = PRule(rule.variable, der, rule.probability)
        self.add_rule(new_rule)
        self.remove_rule(rule)
            
    def convert_long_rules(self, rule, gen):
        while rule.derivation_length() > 2:
            new_var = next(gen)
            short_rule = PRule(rule.variable, [rule.derivation[0],\
                                           new_var], rule.probability)
            new_rule = PRule(new_var, rule.derivation[1:], 1)
            self.add_rule(short_rule)
            self.add_rule(new_rule)
            self.remove_rule(rule)
            self.changes[new_var] = PCFGChange(new_rule, 'auxiliary')
            rule = new_rule
    
    def variable_generator(self):
        i = 1
        while True:
            variable = "X"+str(i)
            while variable in self.rules:
                i += 1
                variable= "X"+str(i)
            yield variable
                
    
    
class PCFGChange(object):
    NEW_START = 'new_start'
    EPSILON_RULE = 'epsilon_rule'
    AUXILIARY = 'auxiliary'

    def __init__(self, rule, change_type, info=None):
        """
        THIS CLASS IS RELEVANT ONLY FOR THE BONUS QUSETION.
        Documents the specific change done on a PCFG.
        """
        assert change_type in (PCFGChange.NEW_START, PCFGChange.EPSILON_RULE, PCFGChange.AUXILIARY)
        self.rule = rule
        self.change_type = change_type
        self.info = info
    
    def __repr__(self):
        return str(self.rule) + self.change_type + str(self.info)
        
def get_from_dic_or_default(dic, key):
    if key in dic:
        return dic[key]
    return 0


