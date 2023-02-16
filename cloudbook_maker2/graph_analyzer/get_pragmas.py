import logging
import os
from pprint import pformat
import ply.lex as lex

def get_pragmas(config_dict):
	logging.debug(">>>Enter in get pragmas")

	config_dict["pragmas"]["du0_functions"] = []
	config_dict["pragmas"]["parallel"] = []
	config_dict["pragmas"]["recursive"] = []
	config_dict["pragmas"]["local"] = []
	config_dict["pragmas"]["nonblocking_def"] = []
	config_dict["pragmas"]["main"] = []

	tokens = ['GLOBAL','NONSHARED','CONST','SAFE',
	'PARALLEL','RECURSIVE','LOCAL','DU0_FUNCTION','NONBLOCKING',
	'NONBLOCKING_INV','SYNC','SYNC_TIME','MAIN','BEGINREMOVE','ENDREMOVE',
	'LOCK','UNLOCK','MAIN_LINE']
	
	#Regex for pragmas: Pragmas for variables and functions must be in the beginning of line
	#Regex for pragmas: Pragmas for invocations and code control can be at any indentation

	t_GLOBAL = r'^\#__CLOUDBOOK:GLOBAL__'
	t_NONSHARED = r'^\#__CLOUDBOOK:NONSHARED__'
	t_CONST = r'^\#__CLOUDBOOK:CONST__'
	t_SAFE = r'^\#__CLOUDBOOK:SAFE__'
	t_PARALLEL = r'^\#__CLOUDBOOK:PARALLEL__'
	t_RECURSIVE = r'^\#__CLOUDBOOK:RECURSIVE__'
	t_LOCAL =  r'^\#__CLOUDBOOK:LOCAL__'
	t_DU0_FUNCTION = r'^\#__CLOUDBOOK:DU0__'
	t_NONBLOCKING = r'^\#__CLOUDBOOK:NONBLOCKING__'
	t_NONBLOCKING_INV = r'^\#__CLOUDBOOK:NONBLOCKING_INV__'
	t_SYNC = r'^[\s]*\#__CLOUDBOOK:SYNC__'
	t_SYNC_TIME = r'^[\s]*\#__CLOUDBOOK:SYNC:[0-9]+__'
	t_MAIN = r'^\#__CLOUDBOOK:MAIN__'
	t_BEGINREMOVE = r'^[\s]*\#__CLOUDBOOK:BEGINREMOVE__'
	t_ENDREMOVE = r'^[\s]*\#__CLOUDBOOK:ENDREMOVE__'
	t_LOCK = r'^[\s]*\#__CLOUDBOOK:LOCK__'
	t_UNLOCK = r'^[\s]*\#__CLOUDBOOK:UNLOCK__'
	t_MAIN_LINE = r'^\w+'

	def t_error(t):
	    #print("Illegal characters!")
	    t.lexer.skip(1)

	lexer = lex.lex()
	token_dict = {}
	input_folder = config_dict["input_dir"]
	files_dict = config_dict["program_files"]
	filenames = get_files(input_folder, files_dict)
	for filename in filenames:
		token_dict[filename] = []
		with open(filename,'r') as fi:
			clean_file_name = filename.replace(input_folder,"").replace(".py","").replace("\\",".").replace("..",".").replace(".","",1)
			#config_dict["program_index"][clean_file_name] = {}
			for i,line in enumerate(fi,start=1):
				lexer.input(line)
				cont = True
				while cont:
					tok = lexer.token()
					if not tok:
						break
					tok.lineno = i
					if tok.lineno in config_dict["program_index"][clean_file_name]:
						pass
					else:
						config_dict["program_index"][clean_file_name][tok.lineno] = []
						if tok.type == "SYNC" or tok.type == "SYNC_TIME":
							config_dict["program_index"][clean_file_name][tok.lineno].append({"type":tok.type,"value":tok.value, "offset":tok.lexpos})
						elif tok.type == "LOCK":
							config_dict["program_index"][clean_file_name][tok.lineno].append({"type":tok.type,"value":tok.value, "offset":tok.lexpos})
						elif tok.type == "UNLOCK":
							config_dict["program_index"][clean_file_name][tok.lineno].append({"type":tok.type,"value":tok.value, "offset":tok.lexpos})
						else:
							config_dict["program_index"][clean_file_name][tok.lineno].append({"type":tok.type,"value":tok.value})#(tok.type,tok.value)
						config_dict["program_index"][clean_file_name] = dict(sorted(config_dict["program_index"][clean_file_name].items(), key=lambda item: item[0]))
						#Get the function invocation info
						if tok.type == 'DU0_FUNCTION':
							if next_token_valido(tok.lineno, config_dict, clean_file_name):
								config_dict["pragmas"]["du0_functions"].append(clean_file_name+"."+config_dict["program_index"][clean_file_name][tok.lineno+1][0]["name"])
							else: logging.warning("WARNING:	Wrong use of cloudbook pragma on line %s: There is no function after the fun definition pragma %s", tok.lineno, 'DU0_FUNCTION')
						if tok.type == 'PARALLEL':
							if next_token_valido(tok.lineno, config_dict, clean_file_name):
								config_dict["pragmas"]["parallel"].append(clean_file_name+"."+config_dict["program_index"][clean_file_name][tok.lineno+1][0]["name"])
							else: logging.warning("WARNING:	Wrong use of cloudbook pragma on line %s: There is no function after the fun definition pragma %s", tok.lineno, 'PARALLEL')
						if tok.type == 'RECURSIVE':
							if next_token_valido(tok.lineno, config_dict, clean_file_name):
								config_dict["pragmas"]["recursive"].append(clean_file_name+"."+config_dict["program_index"][clean_file_name][tok.lineno+1][0]["name"])
							else: logging.warning("WARNING:	Wrong use of cloudbook pragma on line %s: There is no function after the fun definition pragma %s", tok.lineno, 'RECURSIVE')
						if tok.type == 'LOCAL':
							if next_token_valido(tok.lineno, config_dict, clean_file_name):
								config_dict["pragmas"]["local"].append(clean_file_name+"."+config_dict["program_index"][clean_file_name][tok.lineno+1][0]["name"])
							else: logging.warning("WARNING:	Wrong use of cloudbook pragma on line %s: There is no function after the fun definition pragma %s", tok.lineno, 'LOCAL')
						if tok.type == 'NONBLOCKING':
							if next_token_valido(tok.lineno, config_dict, clean_file_name):
								config_dict["pragmas"]["nonblocking_def"].append(clean_file_name+"."+config_dict["program_index"][clean_file_name][tok.lineno+1][0]["name"])
							else: logging.warning("WARNING:	Wrong use of cloudbook pragma on line %s: There is no function after the fun definition pragma %s", tok.lineno, 'NONBLOCKING')
						if tok.type == 'MAIN':
							if next_token_valido(tok.lineno, config_dict, clean_file_name):
								if config_dict["pragmas"]["main"] != []:
									logging.warning("WARNING: The main pragma is used more than once, this may produce a bad execution")
								config_dict["pragmas"]["main"] = clean_file_name+"."+config_dict["program_index"][clean_file_name][tok.lineno+1][0]["name"]
							else: logging.warning("WARNING:	Wrong use of cloudbook pragma on line %s: There is no function after the fun definition pragma %s", tok.lineno, 'MAIN')
	logging.debug("	Pragmas added to the index")
	logging.debug("<<<Exit from get pragmas")		

def get_globals(config_dict):
	logging.debug(">>>Enter in get globals")
	global_var = False
	nonshared_var = False
	const_var = False
	safe_var = False
	config_dict["global_vars"]["global"] = []
	config_dict["global_vars"]["nonshared"] = []
	config_dict["global_vars"]["const"] = []
	config_dict["global_vars"]["safe"] = []
	input_folder = config_dict["input_dir"]
	files_dict = config_dict["program_files"]
	filenames = get_files(input_folder, files_dict)
	for filename in filenames:
		clean_file_name = clean_file_name = filename.replace(input_folder,"").replace(".py","").replace("\\",".").replace("..",".").replace(".","",1)
		for lineno in config_dict["program_index"][clean_file_name]:
			#element = config_dict["program_index"][clean_file_name][lineno]
			for program_element in config_dict["program_index"][clean_file_name][lineno]:
				if program_element["type"] == 'GLOBAL':
					#config_dict["global_vars"]["global"].append(program_element["name"])
					global_var = True
					nonshared_var = const_var = safe_var = False
					continue
				if program_element["type"] == 'NONSHARED':
					#config_dict["global_vars"]["nonshared"].append(program_element["name"])
					nonshared_var  = True
					global_var = safe_var = const_var = False
					continue
				if program_element["type"] == 'CONST':
					#config_dict["global_vars"]["const"].append(program_element["name"])
					const_var = True
					nonshared_var = global_var = safe_var = False
					continue
				if program_element["type"] == 'SAFE':
					#config_dict["global_vars"]["safe"].append(program_element["name"])
					safe_var = True
					nonshared_var = const_var = global_var = False
					continue
				#Si es assign le pongo lo q este a true
				if program_element["type"] == 'assign':
					program_element["type"] = get_global_type(global_var,nonshared_var,const_var,safe_var)
				else:
					global_var = nonshared_var = const_var = safe_var = False
					continue #Si es otra cosa, hago continue

			###GET GLOBAL VARS
		for lineno in config_dict["program_index"][clean_file_name]:
			for program_element in config_dict["program_index"][clean_file_name][lineno]:
				if program_element["type"] == 'global':
					config_dict["global_vars"]["global"].append(program_element["name"])
					continue
				if program_element["type"] == 'nonshared':
					config_dict["global_vars"]["nonshared"].append(program_element["name"])
					continue
				if program_element["type"] == 'const':
					config_dict["global_vars"]["const"].append(program_element["name"])
					continue
				if program_element["type"] == 'safe':
					config_dict["global_vars"]["safe"].append(program_element["name"])
					continue
	logging.debug("	Global var pragmas applied")
	logging.debug(">>>Exit from get globals")
	#print(config_dict["program_index"])

def get_files(input_folder, files_dict):
	filenames = []
	for dir, files in files_dict.items():
		for f in files: 
			dir2=dir.replace("./","")
			filename=input_folder+ os.sep +dir2 + os.sep + f
			if dir2 != "":
				clean_file_name = dir2+"."+f.replace("py","")
			else:
				clean_file_name = f.replace("py","")
			filenames.append(filename)
	return filenames

def get_global_type(global_var,nonshared_var,const_var,safe_var):
	if global_var:
		return "global"
	elif nonshared_var:
		return "nonshared"
	elif const_var:
		return "const"
	elif safe_var:
		return "safe"
	else:
		return "MAIN_LINE"

def next_token_valido(linea, config_dict, file):
	return (linea+1 in config_dict["program_index"][file]) and (config_dict["program_index"][file][linea+1][0]["type"] == "function")


