import logging
import os
import ast
import astunparse
import re

function_invocations = []
translated_functions = {}
function_list = []
file = ""
aux_config_dict = {}
#global vars to generate code in every global declaration inside function
actual_fun_name = ""
actual_fun_fname = ""
du_dest = ""
fun_dest = ""

return_fun = False
#global vars for nonblocking invocations
nonblocking_invocations = {}
nonblocking_function_invocations = []

class invocation_scanner(ast.NodeVisitor):

	def visit_Call(self, node):
		#print(astunparse.unparse(node))
		global function_invocations
		global function_list
		if isinstance(node.func, ast.Name):
			#print("Translator:",node.func.id)
			logging.debug("		The invocation is ast.Name()")
			if file+"."+node.func.id in function_list: #invocacion tipo fun()
				logging.debug("			The invocation %s is correctly in function list", file+"."+node.func.id)
				function_invocations.append(node)
			else: #esta la fun en otro fichero
				aux_func_list = [] #function list without the complete path
				for i in function_list:
					aux_func_list.append(i[i.rfind(".")+1:len(i)])
				apparitions = aux_func_list.count(node.func.id) #apparitions of function in program
				if apparitions == 1:
					#add complete_path_name
					for i in function_list:
						if i[i.rfind(".")+1:len(i)] == node.func.id:
							logging.debug("			The invocation of %s",i)
							function_invocations.append(node)
							break
				elif apparitions > 1:
					logging.error("			ERROR: too many functions with same name")
				else:
					logging.debug("			Is not necessary to translate %s",node.func.id)
		elif isinstance(node.func,ast.Attribute):
			logging.debug("		The invocation is ast.Attribute()")
			if isinstance(node.func.value,ast.Attribute):
				logging.error("			ERROR: more than one abstraction level on call, in progress")
			elif isinstance(node.func.value,ast.Name): #is global_var.fun() ,fun is the attr, global_var is func.value.id
				logging.debug("			The atrribute is ast.Name()")
				if file+"."+node.func.value.id in function_list:
					logging.debug("			The invocation of global var %s is correctly in function list", file+"."+node.func.value.id)
					function_invocations.append(node)
				else: #not global var, is imported_function.fun(), fun is the attr, imported_fun is func.value.id
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(node.func.attr) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == node.func.attr:
								logging.debug("			The invocation of imported function %s", i)
								function_invocations.append(node)
								break
					elif apparitions > 1:
						logging.error("			ERROR: too many functions with same name")
					else:
						logging.debug("			Is not necessary to translate %s",node.func.value.id)
			elif isinstance(node.func.value,ast.Subscript):
				logging.debug("		The invocation attribute is ast.Subscript()")
				#Es un elemento de diccionario o de una lista
				logging.debug("		One level subscript %s",node.func.value.value.id)
				if file+"."+node.func.value.value.id in function_list: #global_var[x].fun()
					function_invocations.append(node)
				else:
					logging.error("		The subscript is not from global var in lineno %s", node.lineno)
				#para ampliar en el futuro
				'''aux_node = node.func.value
				veces=1
				while isinstance(aux_node.value,ast.Subscript):
					veces+=1
					aux_node = aux_node.value
				logging.debug("Madre mia, %s",veces)'''

			else:
				logging.error("		ERROR: Unknown type of invocation in %s",node.lineno)


class RewriteInvocationName(ast.NodeTransformer):

	def visit_Call(self, node):
		global file
		global aux_config_dict
		global function_list
		global actual_fun_name
		global actual_fun_fname
		global du_dest
		global fun_dest
		tabs = "			"
		global_var_modification = False
		global_var_subscript = False
		subscript_index = []
		old_node_node = node
		old_node = astunparse.unparse(node)
		parallel_invocation = False

		#Get name of invoked function
		if isinstance(node.func, ast.Name):
			invoked_fun_name = node.func.id
			node.func.id = "invoker"
				
		elif isinstance(node.func,ast.Attribute):
			if isinstance(node.func.value,ast.Name):
				if file+"."+node.func.value.id in function_list: #global_var.fun() , keep global var
					invoked_fun_name = node.func.value.id
					global_var_modification = True
					global_var_name = node.func.value.id
					global_var_fun = node.func.attr
					node.func = ast.Name()
					node.func.id = "invoker"
					global_var_op = ast.Constant()
					#node.args = []
				else: #file.fun()	keep fun()
					invoked_fun_name = node.func.attr
					node.func = ast.Name()
					node.func.id = "invoker"
			elif isinstance(node.func.value,ast.Subscript):
				invoked_fun_name = node.func.value.value.id
				global_var_modification = True	
				global_var_subscript = True
				subscript_index.append(node.func.value.slice.value)
				global_var_name = node.func.value.value.id
				global_var_fun = node.func.attr
				global_var_slice = node.func.value.slice
				node.func = ast.Name()
				node.func.id = "invoker"

		#Making the invoker dict
		invoked_du = get_invoked_du(invoked_fun_name)
		invoked_fun = get_invoked_fun(invoked_fun_name)
		invoker_fun = actual_fun_fname

		#logging.debug("			%s ==> invoker_%s",node.func.id,translated_functions[file+"."+invoked_fun_name])
		arg_list = get_args_list(node)
		kwargs_dict = get_kwargs_dict(node)

		if file+"."+invoked_fun_name in aux_config_dict["pragmas"]["local"]: #si es local solo cambio nombre, no traduzco
			logging.debug("%sThe function is local, therefore the invocation is not translated into invoker, is resolved locally",tabs)
			node.func.id = translated_functions[file+"."+invoked_fun_name]
			new_node = node
			try:
				new_node.func.id = translated_functions[file+"."+invoked_fun_name]
			except:
				new_node.func.value = translated_functions[file+"."+invoked_fun_name]
			return

		if file+"."+invoked_fun_name in aux_config_dict["pragmas"]["parallel"]: #si es paralela escribo el thread counter
			parallel_invocation = True


		if global_var_modification == True:
			new_list = ast.List()
			new_list.ctx = ast.Load()
			new_list.elts = []
			global_var_version = ast.Constant()
			global_var_version.value = 0
			global_var_version.kind = None
			new_list.elts.append(global_var_version)
			global_var_op = ast.Constant()
			global_var_op.value = "."+global_var_fun
			global_var_op.kind = None
			new_list.elts.append(global_var_op)
			for arg in node.args:
				new_list.elts.append(arg)
			arg_list = new_list

		if global_var_subscript:
			index_const = ast.Constant()
			index_const.value = "index"
			index_const.kind = None
			kwargs_dict.keys.append(index_const)
			list_index = ast.List()
			list_index.ctx = ast.Load()
			list_index.elts = []
			for i in subscript_index:
				list_index.elts.append(i)
			kwargs_dict.values.append(list_index)


		new_dict = ast.Dict()
		new_dict.keys = []
		new_dict.values = []
		for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
			##print(i)
			new_key = ast.Constant()
			new_key.value = i[0]#deberia ser invoked_du, fun y invokerfun
			new_key.kind = None
			new_value = ast.Constant()
			new_value.value = i[1]
			new_value.kind = None
			new_dict.keys.append(new_key)
			new_dict.values.append(new_value)
		
		#creo diccionario de parametros
		params_dict = ast.Dict()
		params_dict.keys = []
		params_dict.values = []
		#creo clave args que meto en el diccionario de parametros
		new_key = ast.Constant()
		new_key.value = "args"
		new_key.kind = None
		new_value = arg_list
		params_dict.keys.append(new_key)
		params_dict.values.append(new_value)
		#todo, crear la key kwargs y meter el dict kwargs
		new_key = ast.Constant()
		new_key.value = "kwargs"
		new_key.kind = None
		new_value = kwargs_dict
		params_dict.keys.append(new_key)
		params_dict.values.append(new_value)
		#Creo Campo params en el diccionario de la invocacion y lo meto
		new_key = ast.Constant()
		new_key.value = 'params'
		new_key.kind = None
		new_value = params_dict
		new_dict.keys.append(new_key)
		new_dict.values.append(new_value)

		node.args = []
		node.keywords = [] #las keywords van al kwargs que hay en args
		node.args.append(new_dict)
		node.func.id = 'invoker' 
		'''new_node = ast.Call()
		new_node.func = ast.Name()
		new_node.func.ctx = ast.Load()
		new_node.args = []
		new_node.args.append(new_dict)
		new_node.func.id = 'invoker'
		new_node.keywords = [] '''

		if global_var_modification:
			node.func.id = old_node+" "*4*node.col_offset+'invoker'
			#node.func.id = old_node+"\t"*node.col_offset+'invoker'
		if parallel_invocation:
			node.func.id = "invoker({'invoked_du': 'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': ['++'], 'kwargs': {}}})\n"+" "*4*node.col_offset+'invoker'
		
		logging.debug("%s	invoker function:  	 %s (%s)",tabs,actual_fun_name,actual_fun_fname)
		logging.debug("%s	invoked function: 	 %s",tabs,invoked_fun)
		logging.debug("%s	invoked du:		 	 %s",tabs,invoked_du)
		logging.debug("%s	args:    		 	 %s",tabs,astunparse.unparse(arg_list).replace("\n",""))
		logging.debug("%s	kwargs:	    	 	 %s",tabs,astunparse.unparse(kwargs_dict).replace("\n",""))
		logging.debug("%s	global var:		 	 %s",tabs,global_var_modification)
		logging.debug("%s	parallel invocation: %s",tabs,parallel_invocation)
		logging.debug("%s	final invocation: 	 %s",tabs,astunparse.unparse(node).replace("\n",""))

class RewriteAssginationsAsInvocations(ast.NodeTransformer):

	def visit_Assign(self, node):
		#logging.debug("ASIGNACION: %s",astunparse.unparse(node))
		global file
		old_node = astunparse.unparse(node)
		clean_file_name = file+"."
		global_var_names = []
		subscript_index = []
		offset = node.col_offset
		old_node = "\t"*offset+old_node

		for var in node.targets:
			if isinstance(var,ast.Name):
				if clean_file_name+var.id in function_list:
					#invocation_list.append({"type":"global","name": clean_file_name+var.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
					global_var_names.append(var.id)
					logging.debug("		Assign %s",clean_file_name+var.id)
				else:
					return node
			elif isinstance(var,ast.Tuple):
				for i in var.elts:
					if clean_file_name+i.id in function_list:
						#invocation_list.append({"type":"global","name": clean_file_name+i.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
						global_var_names.append(i.id)
						logging.debug("		Assign %s",clean_file_name+var.id)
					else:
						return node
			elif isinstance(var,ast.Subscript):
				#comprobar que este en la lista de funciones
				if isinstance(var.value,ast.Name):
					if clean_file_name+var.value.id in function_list:
						#invocation_list.append({"type":"global","name": clean_file_name+var.value.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
						global_var_names.append(var.value.id)
						logging.debug(f"SKYNNET: {old_node}")
						##logging.debug("SKYNNETA VER: %s",var.slice.id)
						##logging.debug("A VER: %s",var.slice.value.id)
						##subscript_index.append(var.slice.value)
						##subscript_index.append(var.slice.id) #Arreglo rapido no funciona el siguiente try except tambien
						try:
							subscript_index.append(var.slice.value)
						except:
							subscript_index.append(var.slice)
						logging.debug("=================OJO===========================")
						logging.debug("		Assign %s",clean_file_name+var.value.id)
					else:
						return node
				else:
					#logging.error("ERROR left part of subscript assignation %s not included in line %s", type(var), node.lineno)
					return node
			else:
				#logging.error("ERROR left part of assignation %s not included in line %s", type(var), node.lineno)
				return node
		logging.debug("		global vars in the assign: %s",global_var_names)

		for global_var_name in global_var_names:
			invoked_du = get_invoked_du(global_var_name)
			invoked_fun = get_invoked_fun(global_var_name)
			invoker_fun = actual_fun_fname#aux_config_dict["function_translated"][clean_file_name+global_var_name]

			new_dict = ast.Dict()
			new_dict.keys = []
			new_dict.values = []
			for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
				new_key = ast.Constant()
				new_key.value = i[0]#deberia ser invoked_du, fun y invokerfun
				new_key.kind = None
				new_value = ast.Constant()
				new_value.value = i[1]
				new_value.kind = None
				new_dict.keys.append(new_key)
				new_dict.values.append(new_value)

			#creao arg_list
			new_list = ast.List()
			new_list.ctx = ast.Load()
			new_list.elts = []
			global_var_version = ast.Constant()
			global_var_version.value = 0
			global_var_version.kind = None
			new_list.elts.append(global_var_version)
			global_var_op = ast.Constant()
			global_var_op.value = "="
			global_var_op.kind = None
			new_list.elts.append(global_var_op)
			###new_list.elts.append(node.value)
			#append el global var name
			##global_var_eq = ast.Name()
			##global_var_eq.id = global_var_name
			##global_var_eq.ctx = ast.Load()
			##new_list.elts.append(global_var_eq)
			new_list.elts.append(node.targets)
			arg_list = new_list
			#creo kwargs_dict
			kwargs_dict = ast.Dict()
			kwargs_dict.keys = []
			kwargs_dict.values = []
			index_const = ast.Constant()
			index_const.value = "index"
			index_const.kind = None
			kwargs_dict.keys.append(index_const)
			list_index = ast.List()
			list_index.ctx = ast.Load()
			list_index.elts = []
			for i in subscript_index:
				logging.debug(f"SKYNNET subscript index {i} {type(i)}") ##Skynnet debug
				list_index.elts.append(i)
			kwargs_dict.values.append(list_index)
			#creo diccionario de parametros
			params_dict = ast.Dict()
			params_dict.keys = []
			params_dict.values = []
			#creo clave args que meto en el diccionario de parametros
			new_key = ast.Constant()
			new_key.value = "args"
			new_key.kind = None
			new_value = arg_list
			params_dict.keys.append(new_key)
			params_dict.values.append(new_value)
			#todo, crear la key kwargs y meter el dict kwargs
			new_key = ast.Constant()
			new_key.value = "kwargs"
			new_key.kind = None
			new_value = kwargs_dict
			params_dict.keys.append(new_key)
			params_dict.values.append(new_value)
			#Creo Campo params en el diccionario de la invocacion y lo meto
			new_key = ast.Constant()
			new_key.value = 'params'
			new_key.kind = None
			new_value = params_dict
			new_dict.keys.append(new_key)
			new_dict.values.append(new_value)

			new_node = ast.Call()
			new_node.func = ast.Name()
			new_node.func.id = "\n"+" "*(4*offset)+'invoker'
			new_node.func.ctx = ast.Load()
			new_node.args = []
			new_node.args.append(new_dict)
			new_node.keywords = []

			tabs = "		"
			logging.debug("%s	invoker function:  	 %s (%s)",tabs,actual_fun_name,actual_fun_fname)
			logging.debug("%s	invoked function: 	 %s",tabs,invoked_fun)
			logging.debug("%s	invoked du:		 	 %s",tabs,invoked_du)
			logging.debug("%s	args:    		 	 %s",tabs,astunparse.unparse(arg_list).replace("\n",""))
			logging.debug(kwargs_dict) ##Debug en skynnet
			logging.debug("%s	kwargs:	    	 	 %s",tabs,astunparse.unparse(kwargs_dict).replace("\n",""))
			#logging.debug("%s	global var:		 	 %s",tabs,global_var_modification)
			#logging.debug("%s	parallel invocation: %s",tabs,parallel_invocation)
			return node,new_node

			#return ast.copy_location(new_node,node)
			#return node,ast.fix_missing_locations(new_node)

	'''def visit_AugAssign(self, node):
		if isinstance(node.target,ast.Name):
			if clean_file_name+node.target.id in function_list:
				invocation_list.append({"type":"global","name": clean_file_name+node.target.id,"line": node.lineno, "offset":node.col_offset, "value": 1})
		else:
			logging.error("ERROR left part of augmented assgination not included in line %s", node.lineno)'''

class RewriteFunctionName(ast.NodeTransformer):

    def visit_FunctionDef(self, node):
    	global file
    	##print("	",node.id,"==>",translated_functions[file+"."+node.id])
    	#node.id = translated_functions[file+"."+node.id]
    	node.name = translated_functions[file+"."+node.name]

class RewriteParallelFunctionName(ast.NodeTransformer):

    def visit_FunctionDef(self, node):
    	global file
    	##print("	",node.id,"==>",translated_functions[file+"."+node.id])
    	#node.id = translated_functions[file+"."+node.id]
    	node.name = "parallel_"+node.name

class RewwriteNonBlockingDefFunctionName(ast.NodeTransformer):

    def visit_FunctionDef(self, node):
    	global file
    	##print("	",node.id,"==>",translated_functions[file+"."+node.id])
    	#node.id = translated_functions[file+"."+node.id]
    	node.name = "nonblocking_"+node.name

class RewriteGlobalDeclaration(ast.NodeTransformer):

    def visit_Global(self, node):
    	global file
    	global actual_fun_name
    	global actual_fun_fname
    	global aux_config_dict
    	##print("	",node.id,"==>",translated_functions[file+"."+node.id])
    	#node.id = translated_functions[file+"."+node.id]
    	global_nodes = []
    	for global_var in node.names:    		
    		#print("Miro la global",global_var)
    		#Es complejo, coge cada "global algo", y lo cambia por el código de cargar la variable. Uso el config dict como aux, porque no puedo pasarlo como parametro
    		if global_var in aux_config_dict["global_vars"]["global"]:
    			logging.debug("			The global declaration of %s will be translated",global_var)
    			global_nodes.append(create_global_declaration_node(global_var,actual_fun_name,actual_fun_fname, aux_config_dict))
    		else:
    			logging.debug("			The global var %s does not need to be translated", global_var)
    			return node
    	return global_nodes 		


def tranlateInvocations(config_dict):
	logging.debug(">>>Enter in translate invocations")
	global translated_functions
	global function_list
	global file
	global function_invocations
	global aux_config_dict
	global actual_fun_name
	global actual_fun_fname

	translated_functions = config_dict["function_translated"]
	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	for function in config_dict["program_data"]["functions"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		actual_fun_name = function
		actual_fun_fname = translated_functions[function]
		function_node = config_dict["program_data"]["functions"][function]
		logging.debug("\n	Checking function %s: %s", function, actual_fun_fname)
		#print("Translator=>Buscamos invocaciones en:",function)
		invocation_scanner().visit(function_node)
		logging.debug("		===All invocations obtained, now translating")
		for invocation in function_invocations:
			logging.debug("		Let's translate %s:	%s",invocation,astunparse.unparse(invocation).replace("\n",""))
			RewriteInvocationName().visit(invocation)
		logging.debug("		===Translate global vars assignations as invocations:")
		RewriteAssginationsAsInvocations().visit(function_node)
		ast.fix_missing_locations(function_node)
		logging.debug("		===Invocations translated")
		#logging.debug("		%s",astunparse.unparse(config_dict["program_data"]["functions"][function]))
		function_invocations = []
		#traduccion de declaracionde variables globales
		translateGlobalDeclaration(config_dict,file,function,function_node)
	logging.debug("=======================")
		

def translateParallelFunctionName(node):
	RewriteParallelFunctionName().visit(node)

def translateNonBlockingDefFunctionName(node):
	RewwriteNonBlockingDefFunctionName().visit(node)

def translateFunctionNames(config_dict):
	global file

	for function in config_dict["program_data"]["functions"]:
		file = function[:function.rfind(".")]
		RewriteFunctionName().visit(config_dict["program_data"]["functions"][function])
	logging.debug("=======================")

def translateGlobalDeclaration(config_dict,file,function,function_node):
	global actual_fun_name
	global actual_fun_fname
	global translated_functions
	global du_dest
	global fun_dest
	global aux_config_dict

	aux_config_dict = config_dict

	actual_fun_name = function
	actual_fun_fname = translated_functions[function]
	#guardamos el nombre de la funcion acualen la que estamos y hacemos el visit
	logging.debug("		===Let's translate global declarations/refresh: global global_var")
	RewriteGlobalDeclaration().visit(function_node)

def create_global_declaration_node_old(global_var,actual_fun_name,actual_fun_fname, config_dict):
	tabs = "				"#4 tabs for logging
	logging.debug("%s Let's write the global var declaration code", tabs)
	global du_dest
	global fun_dest
	#busco la du destino, la funcion destino y todo eso
	for du in config_dict["dus"]:
		for fun in config_dict["dus"][du]:
			if fun[fun.rfind(".")+1:] == global_var:
				du_dest = du
	#du_dest = [du_dest]

	for fun in config_dict["function_translated"]:
		if fun[fun.rfind(".")+1:] == global_var:
			##print("la encuentro")
			fun_dest = config_dict["function_translated"][fun]

	#print("fun_dest",fun_dest)
	
	#invocation_params = "{'invoked_du':\'"+ du_dest+"\','invoked_function':\'"+fun_dest+"\','invoker_function':\'"+ actual_fun_fname+"\','params': {'args':["+'''str('''+actual_fun_fname+'''.ver_'''+global_var+'''),"None"'''+"],'kwargs':{}}}"
	invocation_params = "{'invoked_du':\'"+ du_dest+"\','invoked_function':\'"+fun_dest+"\','invoker_function':\'"+ actual_fun_fname+"\','params': {'args':["+''+actual_fun_fname+'''.ver_'''+global_var+''',"None"'''+"],'kwargs':{}}}"

	code = '''
if not hasattr('''+actual_fun_fname+''', '''+'"'+global_var+'"'+'''):
	'''+actual_fun_fname+"."+global_var+''' = None
if not hasattr('''+actual_fun_fname+''', '''+'"ver_'+global_var+'"'+'''):
	'''+actual_fun_fname+".ver_"+global_var+''' = 0

aux_'''+global_var+''',aux_ver = invoker('''+invocation_params+''')
if aux_'''+global_var+''' != "None":
	'''+actual_fun_fname+"."+global_var+''' = aux_'''+global_var+'''
'''+global_var+''' = '''+actual_fun_fname+"."+global_var+'''
'''+actual_fun_fname+".ver_"+global_var+''' = aux_ver
ver_'''+global_var+''' = '''+actual_fun_fname+".ver_"+global_var+'''
'''
	#print("la convierto en:\n",code)
	logging.debug("%s	invoker function:  	 %s (%s)",tabs,actual_fun_name,actual_fun_fname)
	logging.debug("%s	invoked function: 	 %s",tabs,fun_dest)
	logging.debug("%s	invoked du:		 	 %s",tabs,du_dest)
	logging.debug("%s	args:    		 	 [%s]",tabs,actual_fun_fname+".ver_"+global_var+",'None'")
	logging.debug("%s	kwargs:	    	 	 {}",tabs)
	du_dest = ""
	fun_dest = ""
	return ast.parse(code)

def create_global_declaration_node(global_var,actual_fun_name,actual_fun_fname, config_dict):
	tabs = "				"#4 tabs for logging
	logging.debug("%s Let's write the global var declaration code", tabs)
	global du_dest
	global fun_dest
	#busco la du destino, la funcion destino y todo eso
	for du in config_dict["dus"]:
		for fun in config_dict["dus"][du]:
			if fun[fun.rfind(".")+1:] == global_var:
				du_dest = du
	#du_dest = [du_dest]

	for fun in config_dict["function_translated"]:
		if fun[fun.rfind(".")+1:] == global_var:
			##print("la encuentro")
			fun_dest = config_dict["function_translated"][fun]

	#print("fun_dest",fun_dest)
	
	#invocation_params = "{'invoked_du':\'"+ du_dest+"\','invoked_function':\'"+fun_dest+"\','invoker_function':\'"+ actual_fun_fname+"\','params': {'args':["+'''str('''+actual_fun_fname+'''.ver_'''+global_var+'''),"None"'''+"],'kwargs':{}}}"
	#invocation_params = "{'invoked_du':\'"+ du_dest+"\','invoked_function':\'"+fun_dest+"\','invoker_function':\'"+ actual_fun_fname+"\','params': {'args':["+''+actual_fun_fname+'''.ver_'''+global_var+''',"None"'''+"],'kwargs':{}}}"
	#get if actual fun fname is parallel or nonblocking
	#thi is made after create invocation_paramas dict, therefore the stadistics are correct, indicates f0 as invoker instead of parallel_f0
	old_fun_fname = actual_fun_fname
	for fun in config_dict["function_translated"]:
		if config_dict["function_translated"][fun] == actual_fun_fname:
			orig_actual_fun = fun
		else:#OJO esto es para las nonblocking invocations, que actual_fun_fname ya viene cambiado porque no se puede saber que invocacion es
			orig_actual_fun = ""
	if orig_actual_fun in config_dict["pragmas"]["parallel"]:
		actual_fun_fname = "parallel_"+actual_fun_fname
	if orig_actual_fun in config_dict["pragmas"]["nonblocking_def"]:
		actual_fun_fname = "nonblocking_"+actual_fun_fname
	invocation_params = "{'invoked_du':\'"+ du_dest+"\','invoked_function':\'"+fun_dest+"\','invoker_function':\'"+ old_fun_fname+"\','params': {'args':["+''+actual_fun_fname+'''.ver_'''+global_var+''',"None"'''+"],'kwargs':{}}}"
	code = '''
if not hasattr('''+actual_fun_fname+''', '''+'"'+global_var+'"'+'''):
	'''+actual_fun_fname+"."+global_var+''' = None
if not hasattr('''+actual_fun_fname+''', '''+'"ver_'+global_var+'"'+'''):
	'''+actual_fun_fname+".ver_"+global_var+''' = 0

try:
	aux_'''+global_var+''',aux_ver = invoker('''+invocation_params+''')
except:
	aux_'''+global_var+''',aux_ver = json.loads(invoker('''+invocation_params+'''))
if aux_'''+global_var+''' != "None":
	'''+actual_fun_fname+"."+global_var+''' = aux_'''+global_var+'''
'''+global_var+''' = '''+actual_fun_fname+"."+global_var+'''
'''+actual_fun_fname+".ver_"+global_var+''' = aux_ver
ver_'''+global_var+''' = '''+actual_fun_fname+".ver_"+global_var+'''
'''
	#print("la convierto en:\n",code)
	logging.debug("%s	invoker function:  	 %s (%s)",tabs,actual_fun_name,actual_fun_fname)
	logging.debug("%s	invoked function: 	 %s",tabs,fun_dest)
	logging.debug("%s	invoked du:		 	 %s",tabs,du_dest)
	logging.debug("%s	args:    		 	 [%s]",tabs,actual_fun_fname+".ver_"+global_var+",'None'")
	logging.debug("%s	kwargs:	    	 	 {}",tabs)
	du_dest = ""
	fun_dest = ""
	return ast.parse(code)

def get_invoked_du(fun_name):
	for du in aux_config_dict["dus"]:
		for fun in aux_config_dict["dus"][du]:
			if fun[fun.rfind(".")+1:] == fun_name:
				du_dest = du
	return du_dest

def get_invoked_fun(fun_name):
	for fun in aux_config_dict["function_translated"]:
		if fun[fun.rfind(".")+1:] == fun_name:
			fun_dest = aux_config_dict["function_translated"][fun]
	return fun_dest

def get_args_list(node):
	args_list = ast.List()
	args_list.ctx = ast.Load()
	args_list.elts = []
	for arg in node.args:
		args_list.elts.append(arg)
	return args_list

def get_kwargs_dict_old(node):
	logging.debug("NODE: %s:	%s",node,astunparse.unparse(node))
	kwargs_dict = ast.Dict()
	kwargs_dict.keys = []
	kwargs_dict.values = []
	logging.debug("KWARGS_DICT: %s:	%s",kwargs_dict,astunparse.unparse(kwargs_dict))
	for arg in node.keywords:
		var_value = astunparse.unparse(arg.value)
		var_value = re.sub(r'\s*',"",var_value)
		value = ast.Name()
		value.id = var_value
		value.ctx = ast.Load()
		logging.debug("KEYWORD: %s:	%s",arg.arg,value.id)
		kwargs_dict.keys.append(arg.arg)
		kwargs_dict.values.append(value)
	#logging.debug("KWARGS_DICT: %s:	%s",kwargs_dict,astunparse.unparse(kwargs_dict))
	return kwargs_dict

def get_kwargs_dict(node):
	logging.debug("NODE: %s:	%s",node,astunparse.unparse(node))
	kwargs_dict = ast.Dict()
	kwargs_dict.keys = []
	kwargs_dict.values = []
	'''kwargs_dict.keys = ast.List()
	kwargs_dict.keys.ctx = ast.Load()
	kwargs_dict.keys.elts = []
	kwargs_dict.values = ast.List()
	kwargs_dict.values.ctx = ast.Load()
	kwargs_dict.values.elts = []'''
	logging.debug("KWARGS_DICT1: %s:	%s",kwargs_dict,astunparse.unparse(kwargs_dict))
	for arg in node.keywords:
		logging.debug(node.keywords)
		logging.debug("KEYWORD: %s:	%s",arg.arg,arg.value)
		new_key = ast.Constant()
		new_key.value = arg.arg
		new_key.kind = None
		#kwargs_dict.keys.elts.append(new_key)
		#kwargs_dict.values.elts.append(arg.value)
		kwargs_dict.keys.append(new_key)
		kwargs_dict.values.append(arg.value)
	logging.debug("KWARGS_DICT2: %s:	%s",kwargs_dict,astunparse.unparse(kwargs_dict))
	return kwargs_dict

class visitReturn(ast.NodeVisitor):

	def visit_Return(self, node):
		global return_fun

		logging.debug("Return node: %s",astunparse.unparse(node))
		return_fun = True

class RewriteReturnValue(ast.NodeTransformer):

	def visit_FunctionDef(self, node):
		global aux_config_dict

		translate = False

		logging.debug("		Func name: %s tiene return",(node.name))
		#Si no es local
		if node.name not in aux_config_dict["pragmas"]["local"]:
			translate = True
		for i in aux_config_dict["pragmas"]["local"]:
			if aux_config_dict["function_translated"][i] == node.name:
				translate = False
		if translate == True:
			logging.debug(ast.dump(node.body[-1]))
			for i in node.body:
				if isinstance(i,ast.Return):
					logging.debug("		Return en %s",node.lineno)
					#return_node = ast.Return()
					#return_node.ctx = ast.Load()
					if i.value == None:
						new_value = ast.Constant()
						new_value.value="Cloudbook_done"
						new_value.kind = None
					else:
						new_value = i.value
					i.value = ast.Call()
					i.value.func = ast.Attribute()
					i.value.args = []
					i.value.args.append(new_value)
					i.value.keywords = []
					i.value.func.value = ast.Name()
					i.value.func.value.id = 'json'
					i.value.func.value.ctx = ast.Load()
					i.value.func.attr = 'dumps'
					i.value.func.ctx = ast.Load()
					logging.debug("Queda asi %s",astunparse.unparse(i))
					#i = return_node
		return node

class AddReturnValue(ast.NodeTransformer):

	def visit_FunctionDef(self, node):
		logging.debug("		Func name: %s  no tiene return",(node.name))
		return_fun = False
		return_node = ast.Return()
		return_node.value = ast.Call()
		return_node.value.func = ast.Attribute()
		return_node.value.args = []
		cloudbook_done = ast.Constant()
		cloudbook_done.value = "Cloudbook: Done"
		cloudbook_done.kind = None
		return_node.value.args.append(cloudbook_done)
		return_node.value.keywords = []
		return_node.value.func.value = ast.Name()
		return_node.value.func.value.id = 'json'
		return_node.value.func.value.ctx = ast.Load()
		return_node.value.func.attr = 'dumps'
		return_node.value.func.ctx = ast.Load()
		logging.debug("		Quiero meter %s",astunparse.unparse(return_node))
		node.body.append(return_node)
		#return node.append(return_node)

def translateReturns(config_dict):
	logging.debug("<<<Enter in translate returns")
	global function_list
	global file
	global aux_config_dict
	global return_fun

	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	return_fun = False
	return_node = ast.Return()
	return_node.value = ast.Call()
	return_node.value.func = ast.Attribute()
	return_node.value.args = []
	return_node.value.keywords = []
	return_node.value.func.value = ast.Name()
	return_node.value.func.value.id = 'json'
	return_node.value.func.value.ctx = ast.Load()
	return_node.value.func.attr = 'dumps'
	return_node.value.func.ctx = ast.Load()

	for function in config_dict["program_data"]["functions"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		function_node = config_dict["program_data"]["functions"][function]
		logging.debug("	Checking function %s", function)
		#logging.debug("		",ast.dump(function_node))
		visitReturn().visit(function_node)
		if return_fun:
			RewriteReturnValue().visit(function_node)
		else:
			AddReturnValue().visit(function_node)
		logging.debug("	Returns changed/added")
		return_fun = False
	logging.debug("=======================")


class AddThreadBeforeReturn(ast.NodeTransformer):

	def visit_Return(self, node):

		thread_call = ast.Call()
		thread_dict = ast.Dict()
		thread_dict.keys = []
		thread_dict.values = []

		'''thread_dict.keys.append('invoked_du')
		thread_dict.values.append('du_0')
		thread_dict.keys.append('invoked_function')
		thread_dict.values.append('thread_counter')
		thread_dict.keys.append('invoker_function')
		thread_dict.values.append('thread_counter')
		#thread_dict.keys.append('params')'''

		invoked_du = 'du_0'
		invoked_fun = "thread_counter"
		invoker_fun = "thread_counter"
		for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
			##print(i)
			new_key = ast.Constant()
			new_key.value = i[0]
			new_key.kind = None
			new_value = ast.Constant()
			new_value.value = i[1]
			new_value.kind = None
			thread_dict.keys.append(new_key)
			thread_dict.values.append(new_value)

		new_key = ast.Constant()
		new_key.value = 'params'
		new_key.kind = None
		thread_dict.keys.append(new_key)
		params_dict = ast.Dict()
		params_dict.keys = []
		params_dict.values = []
		#args
		args_const = ast.Constant()
		args_const.value = ('args')
		args_const.kind = None
		params_dict.keys.append(args_const)
		args_value = ast.Constant()
		args_value.value = ['--']
		args_value.kind = None
		params_dict.values.append(args_value)
		#kwargs
		args_const = ast.Constant()
		args_const.value = ('kwargs')
		args_const.kind = None
		params_dict.keys.append(args_const)
		args_value = ast.Dict()
		args_value.keys = []
		args_value.values = []
		params_dict.values.append(args_value)
		thread_dict.values.append(params_dict)

		thread_call.func = ast.Name()
		thread_call.func.id = 'invoker'
		thread_call.func.ctx = ast.Load()
		thread_call.args = []
		thread_call.args.append(thread_dict)
		thread_call.keywords = []

		#self.generic_visit(node)
		#ast.copy_location(thread_call,node)
		node.value = thread_call
		return node

def add_thread_counter_minus(config_dict):
	logging.debug("<<<Adding threading control")
	to_write = "invoker({'invoked_du': 'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': ['++'], 'kwargs': {}}})\n"

	thread_call = ast.Call()
	thread_dict = ast.Dict()
	thread_dict.keys = []
	thread_dict.values = []

	'''thread_dict.keys.append('invoked_du')
	thread_dict.values.append('du_0')
	thread_dict.keys.append('invoked_function')
	thread_dict.values.append('thread_counter')
	thread_dict.keys.append('invoker_function')
	thread_dict.values.append('thread_counter')
	#thread_dict.keys.append('params')'''

	invoked_du = 'du_0'
	invoked_fun = "thread_counter"
	invoker_fun = "thread_counter"
	for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
		##print(i)
		new_key = ast.Constant()
		new_key.value = i[0]
		new_key.kind = None
		new_value = ast.Constant()
		new_value.value = i[1]
		new_value.kind = None
		thread_dict.keys.append(new_key)
		thread_dict.values.append(new_value)

	new_key = ast.Constant()
	new_key.value = 'params'
	new_key.kind = None
	thread_dict.keys.append(new_key)
	params_dict = ast.Dict()
	params_dict.keys = []
	params_dict.values = []
	#args
	args_const = ast.Constant()
	args_const.value = ('args')
	args_const.kind = None
	params_dict.keys.append(args_const)
	args_value = ast.Constant()
	args_value.value = ['--']
	args_value.kind = None
	params_dict.values.append(args_value)
	#kwargs
	args_const = ast.Constant()
	args_const.value = ('kwargs')
	args_const.kind = None
	params_dict.keys.append(args_const)
	args_value = ast.Dict()
	args_value.keys = []
	args_value.values = []
	params_dict.values.append(args_value)
	thread_dict.values.append(params_dict)

	thread_call.func = ast.Name()
	thread_call.func.id = 'invoker'
	thread_call.func.ctx = ast.Load()
	thread_call.args = []
	thread_call.args.append(thread_dict)
	thread_call.keywords = []

	test_const = ast.Constant()
	test_const.value = "pepe"
	test_const.kind = None

	for function in config_dict["program_data"]["functions"]:
		file = function[:function.rfind(".")]
		function_node = config_dict["program_data"]["functions"][function]
		for i in config_dict["function_translated"]: #Los nombres de funcion ya se han cambiado en los nodos
			if config_dict["function_translated"][i] == function_node.name:
				original_node_name = i
		logging.debug("	checking %s",original_node_name)
		if original_node_name in config_dict["pragmas"]["parallel"]:
			logging.debug("	Checking function %s", function)
			##AddThreadBeforeReturn().visit(function_node)
			node = ast.parse("return 0")
			node = function_node
			lista = get_correct_returns(node,[])
			for i in lista:
				AddThreadBeforeReturn().visit(i)
			#print("\n",lista)
			try:
				thread_call.func.id = "\n"+" "*4*function_node.body[-1].col_offset +'invoker'
				function_node.body.insert(len(function_node.body),thread_call)
			except:
				pass
	logging.debug("=======================")


def get_correct_returns(node, return_list):
	for child in ast.iter_child_nodes(node):
		if (isinstance(child,ast.FunctionDef)):
			#return return_list
			continue
		if (isinstance(child,ast.Return)):
			#print("return")
			return_list.append(child)
			#return return_list
		else:
			suma = sum(1 for i in ast.iter_child_nodes(child))
			if suma>0:
				get_correct_returns(child, return_list)
			else:
				#return return_list
				continue
	return return_list
	
	'''print("\nLlamo a la funcion",node)
	suma = sum(1 for i in ast.iter_child_nodes(node))
	print("Tiene",suma,"hijos")
	for child in ast.iter_child_nodes(node):
		print("child",child)
		suma = sum(1 for i in ast.iter_child_nodes(child))
		print("Tiene",suma,"hijos")
		if suma>0:
			#for subchild in ast.iter_child_nodes(child):
			get_correct_returns(child, return_list)'''

class Nonblocking_inv_scannner(ast.NodeVisitor):

	def visit_Call(self, node):
		global nonblocking_invocations
		global nonblocking_function_invocations
		global function_list
		if isinstance(node.func, ast.Name):
			logging.debug("		The invocation is ast.Name()")
			if node.func.id.startswith("nonblocking_inv_",0):
				logging.debug("			Is a nonblocking invocation")
				invocation_name = re.sub(r'nonblocking_inv_\d+_','',node.func.id)
				if file+"."+invocation_name in function_list: #invocacion tipo fun()
					logging.debug("			The invocation %s is correctly in function list", file+"."+invocation_name)
					nonblocking_function_invocations.append(node)
				else: #esta la fun en otro fichero
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(invocation_name) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == invocation_name:
								logging.debug("			The invocation of %s",i)
								nonblocking_function_invocations.append(node)
								break
					elif apparitions > 1:
						logging.error("			ERROR: too many functions with same name")
					else:
						logging.debug("			Is not necessary to translate %s",node.func.id)
		if isinstance(node.func, ast.Attribute):
			logging.debug("		The invocation is ast.Attribute()")
			if isinstance(node.func.value,ast.Attribute):
				logging.error("			ERROR: more than one abstraction level on call, in progress")
			elif isinstance(node.func.value, ast.Name):
				logging.debug("			The atrribute is ast.Name() %s",node.func.value.id)
				if node.func.attr.startswith("nonblocking_inv_",0):
					logging.debug("			Is a nonblocking invocation %s",node.func.attr)
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
								nonblocking_function_invocations.append(node)
								break
					elif apparitions > 1:
						logging.error("			ERROR: too many functions with same name")
				else:
					logging.debug("			Is not necessary to translate %s",node.func.value.id)


		'''if isinstance(node.func,ast.Attribute):
			logging.debug("		The invocation is ast.Attribute()")
			if isinstance(node.func.value,ast.Attribute):
				logging.error("			ERROR: more than one abstraction level on call, in progress")
			elif isinstance(node.func.value,ast.Name): #is global_var.fun() ,fun is the attr, global_var is func.value.id
				logging.debug("			The atrribute is ast.Name()")
				invocation_name = re.sub(r'nonblocking_inv_\d+_','',node.func.value.id)
				if file+"."+node.func.value.id in function_list:
					logging.debug("			The invocation of global var %s is correctly in function list", file+"."+node.func.value.id)
					nonblocking_function_invocations.append(node)
				else: #not global var, is imported_function.fun(), fun is the attr, imported_fun is func.value.id
					aux_func_list = [] #function list without the complete path
					for i in function_list:
						aux_func_list.append(i[i.rfind(".")+1:len(i)])
					apparitions = aux_func_list.count(node.func.attr) #apparitions of function in program
					if apparitions == 1:
						#add complete_path_name
						for i in function_list:
							if i[i.rfind(".")+1:len(i)] == node.func.attr:
								logging.debug("			The invocation of imported function %s", i)
								nonblocking_function_invocations.append(node)
								break
					elif apparitions > 1:
						logging.error("			ERROR: too many functions with same name")
					else:
						logging.debug("			Is not necessary to translate %s",node.func.value.id)'''
		


class RewriteNonblockingInvocationName(ast.NodeTransformer):

	def visit_Call(self, node):
		global file
		global aux_config_dict
		global function_list
		global actual_fun_name
		global actual_fun_fname
		global du_dest
		global fun_dest
		tabs = "			"
		global_var_modification = False
		global_var_subscript = False
		subscript_index = []
		old_node_node = node
		old_node = astunparse.unparse(node)
		parallel_invocation = False

		#Get name of invoked function
		if isinstance(node.func, ast.Name):
			invoked_fun_name = node.func.id
			node.func.id = "invoker"
				
		elif isinstance(node.func,ast.Attribute):
			if isinstance(node.func.value,ast.Name):
				if file+"."+node.func.value.id in function_list: #global_var.fun() , keep global var
					invoked_fun_name = node.func.value.id
					global_var_modification = True
					global_var_name = node.func.value.id
					global_var_fun = node.func.attr
					node.func = ast.Name()
					node.func.id = "invoker"
					global_var_op = ast.Constant()
					#node.args = []
				else: #file.fun()	keep fun()
					invoked_fun_name = node.func.attr
					node.func = ast.Name()
					node.func.id = "invoker"
			elif isinstance(node.func.value,ast.Subscript):
				invoked_fun_name = node.func.value.value.id
				global_var_modification = True	
				global_var_subscript = True
				subscript_index.append(node.func.value.slice.value)
				global_var_name = node.func.value.value.id
				global_var_fun = node.func.attr
				global_var_slice = node.func.value.slice
				node.func = ast.Name()
				node.func.id = "invoker"

		#Making the invoker dict
		#invoked_du = get_invoked_du(invoked_fun_name)
		invoked_du = "du_default"
		#invoked_fun = get_invoked_fun(invoked_fun_name)
		invoked_fun = invoked_fun_name
		invoker_fun = actual_fun_fname

		#logging.debug("			%s ==> invoker_%s",node.func.id,translated_functions[file+"."+invoked_fun_name])
		arg_list = get_args_list(node)
		kwargs_dict = get_kwargs_dict(node)

		if file+"."+invoked_fun_name in aux_config_dict["pragmas"]["local"]: #si es local solo cambio nombre, no traduzco
			logging.debug("%sThe function is local, therefore the invocation is not translated into invoker, is resolved locally",tabs)
			node.func.id = translated_functions[file+"."+invoked_fun_name]
			new_node = node
			try:
				new_node.func.id = translated_functions[file+"."+invoked_fun_name]
			except:
				new_node.func.value = translated_functions[file+"."+invoked_fun_name]
			return

		if file+"."+invoked_fun_name in aux_config_dict["pragmas"]["parallel"]: #si es paralela escribo el thread counter
			parallel_invocation = True


		if global_var_modification == True:
			new_list = ast.List()
			new_list.ctx = ast.Load()
			new_list.elts = []
			global_var_version = ast.Constant()
			global_var_version.value = 0
			global_var_version.kind = None
			new_list.elts.append(global_var_version)
			global_var_op = ast.Constant()
			global_var_op.value = "."+global_var_fun
			global_var_op.kind = None
			new_list.elts.append(global_var_op)
			for arg in node.args:
				new_list.elts.append(arg)
			arg_list = new_list

		if global_var_subscript:
			index_const = ast.Constant()
			index_const.value = "index"
			index_const.kind = None
			kwargs_dict.keys.append(index_const)
			list_index = ast.List()
			list_index.ctx = ast.Load()
			list_index.elts = []
			for i in subscript_index:
				list_index.elts.append(i)
			kwargs_dict.values.append(list_index)


		new_dict = ast.Dict()
		new_dict.keys = []
		new_dict.values = []
		for i in (("invoked_du",invoked_du), ("invoked_function",invoked_fun), ("invoker_function",invoker_fun)):
			##print(i)
			new_key = ast.Constant()
			new_key.value = i[0]#deberia ser invoked_du, fun y invokerfun
			new_key.kind = None
			new_value = ast.Constant()
			new_value.value = i[1]
			new_value.kind = None
			new_dict.keys.append(new_key)
			new_dict.values.append(new_value)
		
		#creo diccionario de parametros
		params_dict = ast.Dict()
		params_dict.keys = []
		params_dict.values = []
		#creo clave args que meto en el diccionario de parametros
		new_key = ast.Constant()
		new_key.value = "args"
		new_key.kind = None
		new_value = arg_list
		params_dict.keys.append(new_key)
		params_dict.values.append(new_value)
		#todo, crear la key kwargs y meter el dict kwargs
		new_key = ast.Constant()
		new_key.value = "kwargs"
		new_key.kind = None
		new_value = kwargs_dict
		params_dict.keys.append(new_key)
		params_dict.values.append(new_value)
		#Creo Campo params en el diccionario de la invocacion y lo meto
		new_key = ast.Constant()
		new_key.value = 'params'
		new_key.kind = None
		new_value = params_dict
		new_dict.keys.append(new_key)
		new_dict.values.append(new_value)

		node.args = []
		node.keywords = [] #las keywords van al kwargs que hay en args
		node.args.append(new_dict)
		node.func.id = 'invoker' 
		'''new_node = ast.Call()
		new_node.func = ast.Name()
		new_node.func.ctx = ast.Load()
		new_node.args = []
		new_node.args.append(new_dict)
		new_node.func.id = 'invoker'
		new_node.keywords = [] '''

		if global_var_modification:
			node.func.id = old_node+" "*4*node.col_offset+'invoker'
			#node.func.id = old_node+"\t"*node.col_offset+'invoker'
		if parallel_invocation:
			node.func.id = "invoker({'invoked_du': 'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': ['++'], 'kwargs': {}}})\n"+" "*4*node.col_offset+'invoker'
		
		logging.debug("%s	invoker function:  	 %s (%s)",tabs,actual_fun_name,actual_fun_fname)
		logging.debug("%s	invoked function: 	 %s",tabs,invoked_fun)
		logging.debug("%s	invoked du:		 	 %s",tabs,invoked_du)
		logging.debug("%s	args:    		 	 %s",tabs,astunparse.unparse(arg_list).replace("\n",""))
		logging.debug("%s	kwargs:	    	 	 %s",tabs,astunparse.unparse(kwargs_dict).replace("\n",""))
		logging.debug("%s	global var:		 	 %s",tabs,global_var_modification)
		logging.debug("%s	parallel invocation: %s",tabs,parallel_invocation)
		logging.debug("%s	final invocation: 	 %s",tabs,astunparse.unparse(node).replace("\n",""))

def add_nonblocking_inv(config_dict):
	logging.debug(">>>Enter in translate nonblocking invocations")

	global function_list
	global nonblocking_invocations
	global translated_functions
	global function_list
	global file
	global nonblocking_function_invocations
	global aux_config_dict
	global actual_fun_name
	global actual_fun_fname

	function_list = config_dict["function_list"]
	nonblocking_invocations = config_dict["nonblocking_invocations"]
	translated_functions = config_dict["function_translated"]
	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	for function in config_dict["program_data"]["functions"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		actual_fun_name = function
		actual_fun_fname = translated_functions[function]
		function_node = config_dict["program_data"]["functions"][function]
		logging.debug("\n	Checking function %s: %s", function, actual_fun_fname)
		Nonblocking_inv_scannner().visit(function_node)
		logging.debug("		===All invocations obtained, now translating")
		#print("\n Invocations nonblock:",nonblocking_function_invocations)
		for invocation in nonblocking_function_invocations:
			logging.debug("		Let's translate %s:	%s",invocation,astunparse.unparse(invocation).replace("\n",""))
			RewriteNonblockingInvocationName().visit(invocation)
		logging.debug("		===Translate global vars assignations as invocations:")
		#RewriteAssginationsAsInvocations().visit(function_node)
		ast.fix_missing_locations(function_node)
		logging.debug("		===Invocations translated")
		#logging.debug("		%s",astunparse.unparse(config_dict["program_data"]["functions"][function]))
		nonblocking_function_invocations = []
		#traduccion de declaracionde variables globales
		#translateGlobalDeclaration(config_dict,file,function,function_node)
	logging.debug("=======================")
		

def translateInvocationsNBF(config_dict):
	logging.debug(">>>Enter in translate invocations for nonblocking invoked functions")
	global translated_functions
	global function_list
	global file
	global function_invocations
	global aux_config_dict
	global actual_fun_name
	global actual_fun_fname

	translated_functions = config_dict["function_translated"]
	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	for function in config_dict["nonblocking_inv_nodes"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		actual_fun_name = function
		actual_fun_fname = translated_functions[function]
		#function_node = config_dict["program_data"]["functions"][function]
		function_node = config_dict["nonblocking_inv_nodes"][function]
		logging.debug("\n	Checking function %s: %s", function, actual_fun_fname)
		#print("Translator=>Buscamos invocaciones en:",function)
		invocation_scanner().visit(function_node)
		logging.debug("		===All invocations obtained, now translating")
		for invocation in function_invocations:
			logging.debug("		Let's translate %s:	%s",invocation,astunparse.unparse(invocation).replace("\n",""))
			RewriteInvocationName().visit(invocation)
		logging.debug("		===Translate global vars assignations as invocations:")
		RewriteAssginationsAsInvocations().visit(function_node)
		ast.fix_missing_locations(function_node)
		logging.debug("		===Invocations translated")
		#logging.debug("		%s",astunparse.unparse(config_dict["program_data"]["functions"][function]))
		function_invocations = []
		#traduccion de declaracionde variables globales
		translateGlobalDeclarationNBF(config_dict,file,function,function_node)
	logging.debug("=======================")

def add_nonblocking_invNBF(config_dict):
	logging.debug(">>>Enter in translate nonblocking invocations")

	global function_list
	global nonblocking_invocations
	global translated_functions
	global function_list
	global file
	global nonblocking_function_invocations
	global aux_config_dict
	global actual_fun_name
	global actual_fun_fname

	function_list = config_dict["function_list"]
	nonblocking_invocations = config_dict["nonblocking_invocations"]
	translated_functions = config_dict["function_translated"]
	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	for function in config_dict["nonblocking_inv_nodes"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		actual_fun_name = function
		actual_fun_fname = translated_functions[function]
		function_node = config_dict["nonblocking_inv_nodes"][function]
		logging.debug("\n	Checking function %s: %s", function, actual_fun_fname)
		Nonblocking_inv_scannner().visit(function_node)
		logging.debug("		===All invocations obtained, now translating")
		#print("\n Invocations nonblock:",nonblocking_function_invocations)
		for invocation in nonblocking_function_invocations:
			logging.debug("		Let's translate %s:	%s",invocation,astunparse.unparse(invocation).replace("\n",""))
			RewriteNonblockingInvocationName().visit(invocation)
		logging.debug("		===Translate global vars assignations as invocations:")
		#RewriteAssginationsAsInvocations().visit(function_node)
		ast.fix_missing_locations(function_node)
		logging.debug("		===Invocations translated")
		#logging.debug("		%s",astunparse.unparse(config_dict["program_data"]["functions"][function]))
		nonblocking_function_invocations = []
		#traduccion de declaracionde variables globales
		#translateGlobalDeclaration(config_dict,file,function,function_node)
	logging.debug("=======================")

def translateGlobalDeclarationNBF(config_dict,file,function,function_node):
	global actual_fun_name
	global actual_fun_fname
	global translated_functions
	global du_dest
	global fun_dest
	global aux_config_dict

	aux_config_dict = config_dict

	actual_fun_name = function
	actual_fun_fname = translated_functions[function]
	actual_fun_fname = "nonblocking_inv_"+actual_fun_fname
	#guardamos el nombre de la funcion acualen la que estamos y hacemos el visit
	logging.debug("		===Let's translate global declarations/refresh: global global_var")
	RewriteGlobalDeclaration().visit(function_node)

def translateReturnsNBF(config_dict):
	logging.debug("<<<Enter in translate returns")
	global function_list
	global file
	global aux_config_dict
	global return_fun

	function_list = config_dict["function_list"]
	aux_config_dict = config_dict

	return_fun = False
	return_node = ast.Return()
	return_node.value = ast.Call()
	return_node.value.func = ast.Attribute()
	return_node.value.args = []
	return_node.value.keywords = []
	return_node.value.func.value = ast.Name()
	return_node.value.func.value.id = 'json'
	return_node.value.func.value.ctx = ast.Load()
	return_node.value.func.attr = 'dumps'
	return_node.value.func.ctx = ast.Load()

	for function in config_dict["nonblocking_inv_nodes"]:
		#get invocations inside functions
		file = function[:function.rfind(".")]
		function_node = config_dict["nonblocking_inv_nodes"][function]
		logging.debug("	Checking function %s", function)
		#logging.debug("		",ast.dump(function_node))
		visitReturn().visit(function_node)
		if return_fun:
			RewriteReturnValue().visit(function_node)
		else:
			AddReturnValue().visit(function_node)
		logging.debug("	Returns changed/added")
		return_fun = False
	logging.debug("=======================")

def translate_nonblocking_functions(config_dict):
	translateInvocationsNBF(config_dict)
	add_nonblocking_invNBF(config_dict)
	translateReturnsNBF(config_dict)
