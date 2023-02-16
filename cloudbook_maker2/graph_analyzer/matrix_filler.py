import logging
import os
from pprint import pformat
import ast
import astunparse
import re

function_list = []
invocation_list = []
clean_file_name = ""
inc = 1
dict_files = {}
dict_imports = {}
global_variables = []

class invocation_scanner(ast.NodeVisitor):

	def visit_Call(self, node):
		global invocation_list
		#print(astunparse.unparse(node))
		if isinstance(node.func,ast.Name):
			#can be a name of function, or a result of an import like from x import *
			#print("Scanner:",node.func.id)
			if clean_file_name+node.func.id in function_list:#function name
				invocation_list.append({"type":"fun","name": clean_file_name+node.func.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
			else:
				aux_func_list = [] #function list without the complete path
				for i in function_list:
					aux_func_list.append(i[i.rfind(".")+1:len(i)])
				apparitions = aux_func_list.count(node.func.id) #apparitions of function in program
				if apparitions == 1:
					#add complete_path_name
					for i in function_list:
						if i[i.rfind(".")+1:len(i)] == node.func.id:
							invocation_list.append({"type":"fun","name": i,"line": node.lineno, "offset":node.col_offset, "value": 1})
							break
				elif apparitions > 1:
					logging.error("ERROR: too many functions with same name")

		elif isinstance(node.func,ast.Attribute):
			if isinstance(node.func.value,ast.Attribute):
				#print("la llamada del atributo",node.func.attr,"es compleja: en proceso")
				logging.error("ERROR: more than one abstraction level on call, in progress")
			elif isinstance(node.func.value,ast.Name): 
				#print("es un atributo",node.func.value.id, node.func.attr)
				if clean_file_name+node.func.value.id in function_list: #for global vars in same file operation
					invocation_list.append({"type":"fun","name": clean_file_name+node.func.value.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
				else: #not global var, is imported_function.fun()
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(node.func.attr) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == node.func.attr:
								invocation_list.append({"type":"fun","name": i,"line": node.lineno, "offset":node.col_offset, "value": 1})
								break
					elif apparitions > 1:
						logging.error("ERROR: too many functions with same name")
			else:
				logging.error("ERROR: Unknown type of invocation in %s",node.lineno)		

		self.generic_visit(node)

class invocation_scanner_extra(ast.NodeVisitor):

	def visit_For(self, node):
		#print("for", node.lineno, node.col_offset)
		invocation_list.append({"type":"loop", "line":node.lineno, "offset": node.col_offset})
		self.generic_visit(node)

	def visit_While(self, node):
		#print("while", node.lineno, node.col_offset)
		invocation_list.append({"type":"loop", "line":node.lineno, "offset": node.col_offset})
		self.generic_visit(node)

	def visit_Global(self,node):
		#print("global", node.lineno, node.col_offset, node.names)
		for i in node.names:
			if clean_file_name+i in function_list:
				invocation_list.append({"type":"global","name": clean_file_name+i,"line": node.lineno, "offset":node.col_offset, "value": 1})
		self.generic_visit(node)

	#for global variables assignation like "global_var = x" or "global_var += 1"
	def visit_Assign(self, node):
		for var in node.targets:
			if isinstance(var,ast.Name):
				if clean_file_name+var.id in function_list:
					#print(astunparse.unparse(node))
					invocation_list.append({"type":"global","name": clean_file_name+var.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
				#program_index[clean_file_name][node.lineno].append({"type":"assign","name":var.id,"value":var_value})
			elif isinstance(var,ast.Tuple):
				for i in var.elts:
					if clean_file_name+i.id in function_list:
						invocation_list.append({"type":"global","name": clean_file_name+i.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
					#program_index[clean_file_name][node.lineno].append({"type":"assign","name":i.id,"value":var_value})
			elif isinstance(var,ast.Subscript):
				if isinstance(var.value,ast.Name):
					if clean_file_name+var.value.id in function_list:
						invocation_list.append({"type":"global","name": clean_file_name+var.value.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
				else:
					logging.error("ERROR left part of subscript assignation %s not included in line %s", type(var), node.lineno)
			else:
				#print("Tipo de parte izquierda",type(var),"de asignacion no comprendido en el fichero tal, en la linea",node.lineno)
				logging.error("ERROR left part of assignation %s not included in line %s", type(var), node.lineno)

	def visit_AugAssign(self, node):
		if isinstance(node.target,ast.Name):
			if clean_file_name+node.target.id in function_list:
				invocation_list.append({"type":"global","name": clean_file_name+node.target.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
		else:
			logging.error("ERROR left part of augmented assgination not included in line %s", node.lineno)

class invocation_scanner_nonblocking_inv(ast.NodeVisitor):

	def visit_Call(self, node):
		global invocation_list
		if isinstance(node.func, ast.Name):
			if node.func.id.startswith("nonblocking_inv_",0):
				invocation_name = re.sub(r'nonblocking_inv_\d+_','',node.func.id)
				if clean_file_name+invocation_name in function_list: #invocacion tipo fun()
					invocation_list.append({"type":"fun","name": clean_file_name+invocation_name,"line": node.lineno, "offset":node.col_offset, "value": 1})
				else: #esta la fun en otro fichero
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(invocation_name) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == invocation_name:
								invocation_list.append({"type":"fun","name": i,"line": node.lineno, "offset":node.col_offset, "value": 1})
								break
					elif apparitions > 1:
						logging.error("			ERROR: too many functions with same name")
		
		if isinstance(node.func, ast.Attribute):
			if isinstance(node.func.value,ast.Attribute):
				logging.error("			ERROR: more than one abstraction level on call, in progress")
			elif isinstance(node.func.value, ast.Name):
				if node.func.attr.startswith("nonblocking_inv_",0):
					invocation_name = re.sub(r'nonblocking_inv_\d+_','',node.func.attr)
					#check if the function exists in other file and is only one
					function_invoked_name = node.func.attr
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(invocation_name) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == invocation_name:
								logging.debug("			The invocation of imported function %s", i)
								#nonblocking_function_invocations.append(node)
								invocation_list.append({"type":"fun","name": i,"line": node.lineno, "offset":node.col_offset, "value": 1})
								break
					elif apparitions > 1:
						logging.error("			ERROR: too many functions with same name")
				#else:
				#	logging.debug("			Is not necessary to translate %s",node.func.value.id)
		self.generic_visit(node)


def get_invocations(config_dict):
	global function_list
	global clean_file_name
	global invocation_list
	global dict_files
	global dict_imports
	global global_variables

	logging.info(">>>Enter in get_invocations")
	input_folder = config_dict["input_dir"]
	files_dict = config_dict["program_files"]
	filenames = get_files(input_folder, files_dict)

	function_list = config_dict["function_list"]
	matrix = create_matrix(function_list)
	dict_files = config_dict["program_files"]
	dict_imports = config_dict["imports"]
	global_variables = config_dict["global_vars"]["global"]
	for ni,i in enumerate(config_dict["program_data"]["functions"]):
		invocation_list = []
		values = [1]
		pos = 0
		last_loop = -1
		last_offset = 1000000
		#print("=======",i,"===========")
		clean_file_name = i[:i.rfind(".")+1] #desde el principio, hasta el punto (punto incluido)
		#print("================="+i+"====================")
		#tree = ast.parse(config_dict["program_data"]["functions"][i])
		function_node = config_dict["program_data"]["functions"][i]
		#print("Scanner=>Buscamos invocaciones en:",i)
		invocation_scanner().visit(function_node)
		invocation_scanner_extra().visit(function_node)
		invocation_scanner_nonblocking_inv().visit(function_node)
		get_invocations_from_tree(function_node, 1, 1, invocation_list)
		logging.debug("	The invocation scanner for file: %s is:	%s", i, invocation_list)
		#get correct values of invocations
		'''for j in invocation_list: #TODO: Quitar esto y hacerlo con visitas recursivas, es mucho mas sencillo
			#if j["type"] == 'global':
			#	continue
			if j["type"] == 'loop':
				values.append(values[len(values)-1]*100) #append last_value * 100
				pos += 1
				last_loop = j["line"]
				last_offset = j["offset"]
			if (j["type"] == 'fun') or (j["type"] == 'global'):
				if j["line"] > last_loop and j["offset"] > last_offset:
					#print(pos)
					j["value"] = values[pos]
			if j["line"] > last_loop and j["offset"] < last_offset:
				pos = 0 if (pos==0) else pos-1
				#pos -=1'''
		#create matrix column
		n = 0
		for j in invocation_list:
			if j["type"] == 'fun' or j["type"] == 'global':
				#print("voy por",j["name"])
				for nfun,fun in enumerate(function_list):
					if j["name"]==fun:
						#print(fun)
						n = nfun				
				matrix[n+1][ni+1] += j["value"]
				#print(function_list[ni],"invoca a",function_list[n])
		#print_matrix(matrix)
	#print_matrix(matrix)
	config_dict["matrix"] = matrix

def create_matrix(function_list):
	num_cols = len(function_list)+1
	num_rows = num_cols
	matrix = [[None] * num_cols for i in range(num_rows)]
	matrix[0][0] = 'Matrix'
	for i in range(1,num_rows):
		matrix[0][i] = function_list[i-1]
	#print matrix[0]
	for i in range(1,num_rows):
		matrix[i][0] = function_list[i-1]
	for i in range(1,num_rows):
		for j in range(1,num_cols):
			matrix[i][j]=0
	return matrix

def print_matrix(matrix):
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	for i in range(0,num_rows):
		print (matrix[i])

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

def get_invocations_from_tree(node, value, acc, invocation_list):
	value = acc*value
	for child in ast.iter_child_nodes(node):
		if isinstance(child,ast.Call):
			#print(child.lineno)
			ind = check_invocation(child.lineno, invocation_list, "fun")
			#print(ind)
			if ind!=-1:
				#print(invocation_list[ind],"=>",value, acc)
				invocation_list[ind]["value"] = value
			continue
		elif isinstance(child,ast.Assign) or isinstance(child,ast.AugAssign):
			ind = check_invocation(child.lineno, invocation_list, "assign")
			#print(ind)
			if ind!=-1:
				#print(invocation_list[ind],"=>",value, acc)
				invocation_list[ind]["value"] = value
				continue
			else:
				get_invocations_from_tree(child,value,acc, invocation_list)	
		elif isinstance(child,ast.For) or isinstance(child,ast.While):
			acc = 100
			get_invocations_from_tree(child,value,acc, invocation_list)
		else:
			acc = 1
			#tener en cuenta las asignaciones, solo de globales
			get_invocations_from_tree(child, value, acc, invocation_list)

def check_invocation(invocation_lineno,invocation_list,check_type):
	if check_type == "fun":
		for ni,i in enumerate(invocation_list):
			#print("=>",ni,i)
			if invocation_list[ni]["type"]=="fun" and invocation_list[ni]["line"]==invocation_lineno:
				return ni
			else:
				continue
		return -1
	elif check_type == "assign":
		for ni,i in enumerate(invocation_list):
			#print("=>",ni,i)
			if invocation_list[ni]["type"]=="global" and invocation_list[ni]["line"]==invocation_lineno:
				return ni
			else:
				continue
		return -1