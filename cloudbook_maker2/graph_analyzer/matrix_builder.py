import logging
import os
import ast
import astunparse
import re
import copy

function_list = []
function_names = []
function_nodes = {}
class_list = []
class_names = []
class_nodes = {}
program_index = {}
clean_file_name = ""
import_dict = {}

class program_scanner(ast.NodeVisitor):

	def visit_FunctionDef(self, node):
		global function_names
		global function_nodes
		function_names.append(node.name)
		function_nodes[node.name] = node
		program_index[clean_file_name][node.lineno] = []
		program_index[clean_file_name][node.lineno].append({"type": "function","name": node.name})

	def visit_ClassDef(self, node):
		global class_names
		global class_nodes
		class_names.append(node.name)
		class_nodes[node.name] = node
		program_index[clean_file_name][node.lineno] = []
		program_index[clean_file_name][node.lineno].append({"type": "class","name":node.name})

	def visit_Assign(self, node):
		#only gets initialization of global vars, therefore augassign is not taken into account
		program_index[clean_file_name][node.lineno] = []
		if not isinstance(node.value,ast.Constant):
			#print("warning")
			logging.warning("	WARNING:	the integrity of the value of the global variable in line %s cannot be verified as it is a complex type",node.lineno)
			for i in node.targets:
				if isinstance(i,ast.Tuple) and isinstance(node.value,ast.Tuple):
					logging.error("	ERROR:	The tuple value in %s could not be assign",node.lineno)
		var_value = astunparse.unparse(node.value)
		var_value = re.sub(r'\s*',"",var_value)
		for var in node.targets:
			if isinstance(var,ast.Name):
				program_index[clean_file_name][node.lineno].append({"type":"assign","name":var.id,"value":var_value})
			elif isinstance(var,ast.Tuple):
				for i in var.elts:
					program_index[clean_file_name][node.lineno].append({"type":"assign","name":i.id,"value":var_value})
			else:
				#print("Tipo de parte izquierda",type(var),"de asignacion no comprendido en el fichero tal, en la linea",node.lineno)
				logging.error("left part of assignation %s not included in line %s", type(var), node.lineno)

	def visit_Import(self, node):
		#print("Import: ", node.lineno, node.col_offset, node.names, len(node.names))
		program_index[clean_file_name][node.lineno] = []
		for i in node.names:
			#print(i.name, i.asname)
			import_dict[clean_file_name].append({"type":"import","name":i.name,"alias":i.asname})
			program_index[clean_file_name][node.lineno].append({"type":"import","name":i.name,"alias":i.asname})#(("import", (i.name, i.asname)))

	def visit_ImportFrom(self, node):
		program_index[clean_file_name][node.lineno] = []
		for i in node.names:
			program_index[clean_file_name][node.lineno].append({"type":"fromimport","name":i.name,"alias":i.asname,"module":node.module,"level":node.level})
			import_dict[clean_file_name].append({"type":"fromimport","name":i.name,"alias":i.asname,"module":node.module,"level":node.level})
			#(("fromimport", (i.name, i.asname), node.module, node.level))

def get_program_info(config_dict):
	'''This function gets the function list and nodes for all functions and classes
	to every function or class gets his full path name
	it also start creation of program index, with global vars (assignation) and imports'''
	global function_list
	global function_names
	global function_nodes
	global class_list
	global class_names
	global class_nodes
	global clean_file_name

	logging.debug(">>>Enter in get_program_info")
	input_folder = config_dict["input_dir"]
	files_dict = config_dict["program_files"]
	filenames = get_files(input_folder, files_dict)

	for filename in filenames:
		logging.debug(f"	Searching in {filename} for classes and functions")
		clean_file_name = filename.replace(input_folder,"").replace(".py","").replace("\\",".").replace("..",".").replace(".","",1)
		logging.debug("	Clean file name: %s",clean_file_name)
		program_index[clean_file_name] = {}
		import_dict[clean_file_name] = []
		#with open(filename,"r") as source:
		remove_lines = False
		source = ""
		source_file = open(filename, "r")
		nonblocking_inv = False
		nonblocking_inv_index = 0
		for line in source_file:
			'''if remove_lines:
				#print("remove lines activo",line)
				logging.debug("Line removed: %s",line)
				line = line.strip()
				if "#" not in line:
					source += "#"+line
					print("#"+line)
				else:
					source += line'''
			if "#__CLOUDBOOK:SYNC__" in line:
				source += line.replace("#__CLOUDBOOK:SYNC__", "CLOUDBOOK_SYNC()")
				continue
			elif '#__CLOUDBOOK:SYNC:' in line:
				index_init = line.rfind(":")+1
				index_end = line.rfind("_")-1
				t = line[index_init:index_end]
				source+=re.sub(r'\#__CLOUDBOOK:SYNC:[0-9]+__',"CLOUDBOOK_SYNC("+t+")",line)
				continue
				#source += line.replace("#__CLOUDBOOK:SYNC__", "CLOUDBOOK_SYNC(t)")
			elif '#__CLOUDBOOK:LOCK__' in line:
				source+=re.sub(r'\#__CLOUDBOOK:LOCK__','CLOUDBOOK_LOCK()',line)
				continue
			elif '#__CLOUDBOOK:UNLOCK__' in line:
				source+=re.sub(r'\#__CLOUDBOOK:UNLOCK__','CLOUDBOOK_UNLOCK()',line)
				continue
			elif ("#__CLOUDBOOK:BEGINREMOVE__" in line) and ("##" not in line):
				remove_lines = True
				source+=line #is written in order to not change the source code (it will be used to get pragmas)
			elif ("#__CLOUDBOOK:ENDREMOVE__" in line) and ("##" not in line):
				remove_lines = False
				source+=line #is written in order to not change the source code (it will be used to get pragmas)
			elif "__CLOUDBOOK__" in line:
				if not remove_lines:
					source+=line.replace("__CLOUDBOOK__","__CLOUDBOOK__()")
				else:
					logging.debug("Line removed: %s",line)
					source+="#"+line #SKYNNET: Si quieres eliminar lineas que usan la vble cloudbook
				continue
			elif "__CLOUDBOOK:NONBLOCKING_INV__" in line:
				source+=line
				nonblocking_inv = True
				continue
			#if remove_lines == True: #TODO esto deberia estar debajo, pero no se mete en el else
				#logging.debug("Line removed: %s",line)
				#line = line.strip()
				#source += "#"+line
				#print("#"+line)
			else:
				if nonblocking_inv and not remove_lines:
					line_tabs = line.rstrip().count("\t")
					if line.find(".") == -1:
						new_line = "\t"*line_tabs+"nonblocking_inv_"+str(nonblocking_inv_index)+"_"+re.sub(r'\s','',line)+"#" #comment the original line, written in next if
						source += new_line
						###GET PRAGMA IN CONFIG DICT
						invocation_fun = re.sub(r'\s','',line)
						invocation_fun = invocation_fun[:invocation_fun.find("(")]
						function_name = clean_file_name +"."+ invocation_fun
						if function_name not in config_dict["nonblocking_invocations"]:
							config_dict["nonblocking_invocations"][function_name]=[]
						config_dict["nonblocking_invocations"][function_name].append("nonblocking_inv_"+str(nonblocking_inv_index)+"_"+invocation_fun)
						###EXIT FROM GET PRAGMA IN CONFIG DICT
						nonblocking_inv = False
						nonblocking_inv_index += 1
					else:
						aux_line_pre = line[:line.rfind(".")+1]
						aux_line_post = line[line.rfind(".")+1:]
						aux_line_pre = re.sub(r'\s','',aux_line_pre)
						aux_line_post = re.sub(r'\s','',aux_line_post)
						new_line = "\t"*line_tabs+aux_line_pre+"nonblocking_inv_"+str(nonblocking_inv_index)+"_"+aux_line_post+"#" #comment the original line, written in next if
						source += new_line
						###GET PRAGMA IN CONFIG DICT
						invocation_fun = aux_line_post
						invocation_fun = invocation_fun[:invocation_fun.find("(")]
						function_name = aux_line_pre + invocation_fun
						if function_name not in config_dict["nonblocking_invocations"]:
							config_dict["nonblocking_invocations"][function_name]=[]
						config_dict["nonblocking_invocations"][function_name].append("nonblocking_inv_"+str(nonblocking_inv_index)+"_"+invocation_fun)
						###EXIT FROM GET PRAGMA IN CONFIG DICT
						nonblocking_inv = False
						nonblocking_inv_index += 1
				if not remove_lines:
					source += line
				else:#TODO: No se mete por este else
					logging.debug("Line removed: %s",line)
					#line = line.strip()
					source += "#"+line
		
		#file to test the source code in "source"
		#new_code_name = "codigonuevo"+clean_file_name+".py"
		#ftest = open(new_code_name,"w")
		#ftest.write(source)
		#ftest.close()

		#tree = ast.parse(source.read())
		tree = ast.parse(source)
		program_scanner().visit(tree)
		for function in function_names: #Use complete function names
			function_list.append(clean_file_name+"."+function)
			function_nodes[clean_file_name+"."+function] = function_nodes.pop(function)
		for class_name in class_names: #Use complete class names
			class_list.append(clean_file_name+"."+class_name)
			class_nodes[clean_file_name+"."+class_name] = class_nodes.pop(class_name)
		function_names = []
		class_names = []

	logging.debug(f"Function_list: {function_list}")
	logging.debug(f"Class_list: {class_list}")
	config_dict["function_list"] = function_list
	config_dict["program_data"]["functions"] = function_nodes
	config_dict["program_data"]["classes"] = class_nodes
	config_dict["program_index"] = program_index
	config_dict["imports"] = import_dict
	#nonblocking invocations node
	for i in config_dict["nonblocking_invocations"]:
		config_dict["nonblocking_inv_nodes"][i] = copy.deepcopy(function_nodes[i])
	#Max threads value
	config_dict["max_threads"] = config_dict["max_threads"] * config_dict["num_dus"] if not config_dict["agent0_only_du0"] else config_dict["max_threads"] * (config_dict["num_dus"]-1)
	#logging.debug('Program_index:')
	#log_program_index(config_dict)
	logging.debug(">>>Exit from get functions\n")


def file_scanner(config_dict): #TODO remake this function correctly
	'''This function gathers all the files from the source code'''
	logging.debug(">>>Enter in file_scanner...")
	input_folder = str(config_dict["input_dir"])
	#Aux variables
	directory="../../"+input_folder
	file_dictionary = {}
	files1=[]
	files2=[]
	files3=[]
	dict_files={}
	rootDir = directory
	rootDir = input_folder
	#Walk the input path
	for dirName, subdirList, fileList in os.walk(rootDir):
		dirName=dirName.replace(rootDir+os.sep,"./")
		dirName=dirName.replace(rootDir,"./") # root
		if "__pycache__" in dirName:
			continue
		files2=[]
		for fname in fileList:			
			if fname.find(".pyc")==-1 and fname.find(".py")!=-1 and fname[0:2].find("__")==-1: 
				#python internal files are ignored
				files2.append(fname)
		dict_files[dirName]=files2
	logging.debug("Program files:")
	for i in dict_files:
		logging.debug("	%s ==> %s",i,dict_files[i])
	logging.debug(">>>Exit from file_scanner...\n")
	return dict_files

def get_files(input_folder, files_dict):
	logging.debug("	>>>Auxiliar function to get filenames")
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
	logging.debug("		Filenames: %s", filenames)
	logging.debug("	<<<Exit from get files")
	return filenames

def get_function_list(config_dict):
	logging.debug(">>>Enter in get function list")
	for filename in config_dict["program_index"]:
		for lineno in config_dict["program_index"][filename]:
			for program_element in config_dict["program_index"][filename][lineno]:
				if program_element["type"] == "global":
					config_dict["function_list"].append(filename+"."+program_element["name"])#append(filename+"_VAR_"+program_element["name"])
	logging.debug("	Global vars added to function list")
	logging.debug("<<<Exit from get function list\n")


def log_program_index(config_dict):
	for file in config_dict['program_index']:
		logging.debug("In file: %s",file)
		for nline in config_dict['program_index'][file]:
			logging.debug("	%s:	%s",nline,config_dict['program_index'][file][nline])