from ast import parse
import os
from unittest.util import three_way_cmp
from venv import create
from tree_sitter import Language, Parser
from fuzzywuzzy import fuzz
import re
import json

function_names = ["incr"]
PYTHON = "PYTHON"
JAVA = "JAVA"
CPP = "CPP"

Language.build_library(
    # Store the library in the `build` directory
    'build/my-languages.so',

    # Include one or more languages
    #Jonas
    #[
    #    '/Users/jonas/Documents/GitHub/tree-sitter-cpp',
    #    '/Users/jonas/Documents/GitHub/tree-sitter-java',
    #    '/Users/jonas/Documents/GitHub/tree-sitter-python'
    #]
    #Vivian
    [
        '/home/vivi/src/tree-sitter-python',
        '/home/vivi/src/tree-sitter-java',
        '/home/vivi/src/tree-sitter-cpp'
    ]
)

PY_LANGUAGE = Language('build/my-languages.so', 'python')
JV_LANGUAGE = Language('build/my-languages.so', 'java')
CPP_LANGUAGE = Language('build/my-languages.so', 'cpp')

"""Create Parser"""
parser_py = Parser()
parser_py.set_language(PY_LANGUAGE)

parser_jv = Parser()
parser_jv.set_language(JV_LANGUAGE)

parser_cpp = Parser()
parser_cpp.set_language(CPP_LANGUAGE)


class RuleSet:
    # Initializing
    def __init__(self):
        self.parse_tree_dict = {}
        if not os.path.isfile("rule-set.json"):
            self.create_parse_tree_dict()
        else:
            with open("rule-set.json") as file:
                self.parse_tree_dict = json.load(file)
                print(f"Loading the Rule Set ... Done ... Its length is {len(self.parse_tree_dict)}")

    # Destructor
    """def __del__(self):
        with open("rule-set.json", "w+") as file:
            json.dump(self.parse_tree_dict, file, indent=4)
        #self.save_parse_tree_dict() # or create a separate function"""

    def create_parse_tree_dict(self):
        ''''predefine basic rules'''
        self.parse_tree_dict = {"ALLOCATION": {parser_py.parse(bytes("b = 5", "utf-8")).root_node.sexp(): "name = value",
                                               parser_jv.parse(bytes("int b = 5;", "utf-8")).root_node.sexp(): "type name = value;",
                                               parser_cpp.parse(bytes("int b = 5;", "utf-8")).root_node.sexp(): "type name = value;"
                                               }
                                }

    def save_parse_tree_dict(self):
        with open("rule-set.json", "w+") as file:
            json.dump(self.parse_tree_dict, file, indent=4)

    def create_generic_code_expression(self, code):
        generic_code = code

        value = return_value(code)
        if value:
            generic_code = generic_code.replace(value, "value")

        operator = return_operator(code)
        if operator:
            generic_code = generic_code.replace(operator, "operator")

        type = return_type(code)
        if type:
            generic_code = generic_code.replace(type, "type")

        names = return_name(code)
        if len(names) == 1:
            generic_code = generic_code.replace(names[0], "name")
        else:
            for i, name in enumerate(names):
                    generic_code = generic_code.replace(name, "name_"+str(i))
        return generic_code

    def add_rule(self, py_code, jv_code, cpp_code, rule_name):
        generic_py_code = self.create_generic_code_expression(py_code)
        generic_jv_code = self.create_generic_code_expression(jv_code)
        generic_cpp_code = self.create_generic_code_expression(cpp_code)

        self.parse_tree_dict.update({rule_name: {parser_py.parse(bytes(py_code, "utf-8")).root_node.sexp(): generic_py_code,
                                            parser_jv.parse(bytes(jv_code, "utf-8")).root_node.sexp(): generic_jv_code,
                                            parser_cpp.parse(bytes(cpp_code, "utf-8")).root_node.sexp(): generic_cpp_code
                                            }
                                    })

    def complete_simple_rules(self):
        for func_name in function_names:
            with open("data/"+func_name+".py", 'r') as py, open("data/"+func_name+".java", 'r') as jv, open("data/"+func_name+".cpp", "r") as cpp:
                for line_py, line_jv, line_cpp in zip(py, jv, cpp):
                    parse_tree, input_code = create_parse_tree(line_jv, JAVA)
                    if rule_set.rule_match(parse_tree)[0]:
                        continue 
                    rule_name = str(input(f"Please enter the rule name for '{input_code[:-1]}': "))
                    while rule_name in self.parse_tree_dict:
                        rule_name = str(input("This name is aleady in the database... Please enter another one: "))
                    rule_set.add_rule(line_py, line_jv, line_cpp, rule_name)  

    def rule_match(self, input_parse_tree):
        for rule_name in self.parse_tree_dict:
            for sexp_tree in self.parse_tree_dict[rule_name]:
                if fuzz.ratio(sexp_tree, input_parse_tree) >= 95:
                    return True, rule_name
        return False, ""

    def translate(self, input_code, rule_name):
        translations = []
        for sexp_tree in self.parse_tree_dict[rule_name]:
            entry = self.parse_tree_dict[rule_name][sexp_tree]

            value = return_value(input_code)
            if value:
                entry = entry.replace("value", value)

            operator = return_operator(input_code)
            if operator:
                entry = entry.replace("operator", operator)

            type = return_type(input_code)
            if type:
                entry = entry.replace("type", type)            
        
            names = return_name(input_code)
            if len(names) == 1:
                entry = entry.replace("name", names[0])
            else:
                for i, name in enumerate(names):
                    entry = entry.replace("name_"+str(i), name)
            translations.append(entry)

        return translations
    # check for best fitting parse-tree and "apply rule" aka get value for key
    # and then get type, name, and value for variables
    # and then party time


def create_parse_tree(input_code, input_language):
    if input_language == "PYTHON":
        return parser_py.parse(bytes(input_code, "utf-8")).root_node.sexp(), input_code
    elif input_language == "JAVA":
        return parser_jv.parse(bytes(input_code, "utf-8")).root_node.sexp(), input_code
    elif input_language == "CPP":
        return parser_cpp.parse(bytes(input_code, "utf-8")).root_node.sexp(), input_code


def return_type(input_string):
    '''
    check for type if it is contained in string 
    or check for type of number in python
    '''
    types = ["int", "float", "double"]
    for type in types:
        if type in input_string:
            return type
    number = return_value(input_string)
    if number:
        if re.search(r"\.", number) is None:
            return "int"
        elif len(number) < 9: 
            return "float" # 6-7 significant digits
        return "double" # 15-16 significant digits
    return None


def return_value(input_string):
    '''
    returns value from given string
    '''
    number = re.findall(r'\d+(?:\.\d+)?', input_string)
    return number[0] if number else None


def return_name(input_string):
    string = re.sub('\d', '', input_string)
    string = string.replace(return_operator(string), "")
    string = string.replace(";", "")
    string = string.replace("=", "")
    string = string.replace(".", "")
    types = ["int", "float", "double"]
    for type in types:
        string = string.replace(type, "")
    names = re.findall('[a-z,_,A-Z]*', string)
    
    return [name for name in names if name]


def return_operator(input_string):
    arithmetic_operators = ["+", "-", "*", "/", "%", "**", "//"]
    for operator in arithmetic_operators:
        if operator in input_string:
            return operator
    return None

#Jonas
"""def return_name(input_string):
    '''
    filter out name of variable
    '''
    string = re.sub('\d', '', input_string)
    string = string.replace(";", "")
    string = string.replace("=", "")
    string = string.replace(" ", "")
    string = string.replace(".", "")
    types = ["int", "float", "double"]
    for type in types:
        string = string.replace(type, "")
    return string"""





rule_set = RuleSet()
rule_set.complete_simple_rules()

# added for better/ faster testing
while True: 
    user_code = str(input("Please enter a code to be translated or exit: "))
    if user_code == "exit":
        break
    user_code_language = str(input("Please enter the programming language the code above is written in: "))
    while user_code_language not in [PYTHON, JAVA, CPP]:
        user_code_language = str(input("Please enter correct programming language: "))

    parse_tree, input_code = create_parse_tree(user_code, user_code_language)
    rule_found, rule_name = rule_set.rule_match(parse_tree)
    if rule_found:    
        translations = rule_set.translate(input_code, rule_name)
        print("PYTHON: " + translations[0])
        print("JAVA: " + translations[1])
        print("CPP: " + translations[2])
    else: 
        print(f"No appropriate rule for translating '{user_code[:-1]}' was found in the database...")

rule_set.save_parse_tree_dict()

