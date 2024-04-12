#generate de dus
#por cada du, miro imports (meto todos menos los de la antigua forma), miro cada funcion
	#veo si hay etiquetas y trato las invocaciones
	#en la du_0 meto el main
import logging
import os
import ast
import astunparse
import copy

from . import translator

function_invocations = []
aux_function_list = []

function_list = []
file = ""
translate_functions={}

def create_du(du_name,config_dict):
	global function_invocations
	global file
	global function_list
	global translated_functions

	translated_functions = config_dict["function_translated"]
	function_list = config_dict["function_list"]
	filename = config_dict["output_dir"]+os.sep+du_name+".py"
	f = open(filename, "w")

	#write imports
	f.write("import threading\n")
	f.write("import json\n")
	f.write("import time\n")
	remove_unused_imports(config_dict)
	logging.debug("Final imports: %s",config_dict["imports"])
	for file in config_dict["imports"]:
		##print(file)
		for import_element in config_dict["imports"][file]:
			##print(import_element)
			if import_element["type"] == 'fromimport':
				if import_element["level"] == 0:
					cad = "from "+ import_element["module"]+" import "+import_element["name"]
					if import_element["alias"] is not None:
						cad = cad + " as " + import_element["alias"]
					f.write(cad+"\n")
			else:
				cad = "import "+ import_element["name"]
				if import_element["alias"] is not None:
						cad = cad + " as " + import_element["alias"]
				f.write(cad+"\n")

			#f.write(astunparse.unparse(import_element))
	#f.write("invoker = None")
	#write global vars
	#nonshared y const
	#for i in config_dict["globals"]["nonshared"]:
	for file in config_dict["program_index"]:
		for line in config_dict["program_index"][file]:
			#print(line)
			if config_dict["program_index"][file][line][0]["type"] == 'nonshared':
				f.write(config_dict["program_index"][file][line][0]["name"]+" = "+config_dict["program_index"][file][line][0]["value"]+"\n")
			if config_dict["program_index"][file][line][0]["type"]	== 'const':
				f.write(config_dict["program_index"][file][line][0]["name"] +" = "+config_dict["program_index"][file][line][0]["value"]+"\n")

	#global y safe
	for single_class in config_dict["program_data"]["classes"]:
		f.write(astunparse.unparse(config_dict["program_data"]["classes"][single_class]))
		f.write("\n")
	for function in config_dict["dus"][du_name]:
		file = function[:function.rfind(".")]
		if function[function.rfind(".")+1:] in config_dict["global_vars"]["global"]:
			#function_global = function[function.rfind(".")+1:]
			#escribir definicion de la funcion
			f.write(global_def_fun(config_dict,function))
		if function in config_dict["pragmas"]["parallel"]: #si es paralela escribo la funcion lanzahilos, y traduzco el nombre de la parallel
			#escribo el lanza hilos, y cambio nombre al nodo
			function_name = config_dict["program_data"]["functions"][function].name
			function_args = astunparse.unparse(config_dict["program_data"]["functions"][function].args).replace("\n","")
			function_args_node = config_dict["program_data"]["functions"][function].args
			function_def = "\ndef "+function_name+"("+function_args+"):"
			function_body = function_body_text(config_dict, function_name, function_args, function_args_node)
			f.write(function_def+function_body)
			#renombro la parallel por parallel_fx
			translator.translateParallelFunctionName(config_dict["program_data"]["functions"][function])
			#TODO el lock para hacer solo una funcion paralela, se escribe aqui la funcion como he hecho con la anterior, escribo el def y unparseo el body, y el return si tiene
		if function in config_dict["pragmas"]["nonblocking_def"]:
			#escribo el lanza hilos, y cambio nombre al nodo
			function_name = config_dict["program_data"]["functions"][function].name
			function_args = astunparse.unparse(config_dict["program_data"]["functions"][function].args).replace("\n","")
			function_args_node = config_dict["program_data"]["functions"][function].args
			function_def = "\ndef "+function_name+"("+function_args+"):"
			function_body = function_body_text(config_dict, function_name, function_args, function_args_node, "nonblocking")
			f.write(function_def+function_body)
			#renombro la parallel por parallel_fx
			translator.translateNonBlockingDefFunctionName(config_dict["program_data"]["functions"][function])
		if function in config_dict["program_data"]["functions"]: #Escribo las funciones de la du tal cual estan los nodos
			##print("Voy a escribir en",du_name,"la funcion", function)
			cadena = astunparse.unparse(config_dict["program_data"]["functions"][function])
			f.write(cadena)
	f.write(cloudbook_sync_code(config_dict))
	f.write(cloudbook_critical_section_code())
	if filename == config_dict["output_dir"]+os.sep+"du_default.py":
		noblocking_invocations_thread_launcher(config_dict,f)
		noblocking_invocations_target_code(config_dict,f)
	if filename == config_dict["output_dir"]+os.sep+"du_0.py":
		f.write(du0_thread_counter(config_dict))
		f.write(du0_critical_section_control())
		f.write(d0_main(config_dict))

def d0_main(config_dict):
	return '''
def main():
	return '''+translated_functions[config_dict["pragmas"]["main"]]+"()"+'''
\n'''

def function_body_text(config_dict, function_name, function_args, function_args_node, function_type = "parallel"): #Es necesario el return?
	#func_args = function_args.vararg
	#func_args = astunparse.unparse(func_args)
	#func_kwargs = function_args.kwarg
	#func_kwargs = astunparse.unparse(func_kwargs)
	##print("ARGUMENTOS:",ast.dump(function_args_node))
	kwargs_len = len(function_args_node.defaults)
	args_len = len(function_args_node.args)
	kwargs_dict = {}
	kwargs_dict2 = ast.Dict()
	kwargs_dict2.keys = []
	kwargs_dict2.values = []
	function_args2 = []
	function_args3 = ""
	if kwargs_len > 0:
		##print("Hay",len(function_args_node.defaults),"kwargs")
		for i in range(1,kwargs_len+1):
			aux_name = ast.Name()
			aux_name.ctx = ast.Load()
			aux_name.id = function_args_node.args[-i].arg
			aux_key = ast.Constant()
			aux_key.kind = None
			aux_key.value = function_args_node.args[-i].arg
			#kwargs_dict[function_args_node.args[-i].arg] = function_args_node.args[-i].arg
			#kwargs_dict[function_args_node.args[-i].arg] = function_args_node.defaults[-i].value
			kwargs_dict2.keys.append(aux_key)
			kwargs_dict2.values.append(aux_name)
	kwargs_dict2 = astunparse.unparse(kwargs_dict2).replace("\n","")
	##print("KWARGS_DICT:",kwargs_dict)
	##print("KWARGS_DICT2:",kwargs_dict2)
	for i in range(len(function_args_node.args)-kwargs_len):
		function_args2.append(function_args_node.args[i].arg)
	##print("ARGS_LIST:", function_args)
	for i in range(len(function_args_node.args)-kwargs_len):
		function_args3 += function_args_node.args[i].arg
		if i < (len(function_args_node.args)-kwargs_len)-1:
			function_args3 += ", "
	##print("ARGS_LIST:", function_args3)

	thread_name = "thread" + function_name
	if function_type == "parallel":
		target_name = "parallel_" + function_name
	elif function_type == "nonblocking":
		target_name = "nonblocking_" + function_name
	elif function_type == "nonblocking_inv":
		target_name = "nonblocking_inv_" + function_name
	if function_type == "parallel" and config_dict["max_threads"] == 0:
		return '''
	'''+thread_name+''' = threading.Thread(target= '''+target_name+''', daemon = False, args = ['''+function_args3+'''], kwargs='''+kwargs_dict2+''')
	'''+thread_name+'''.start()
	return json.dumps("cloudbook: thread launched")
'''
	elif function_type == "parallel" and config_dict["max_threads"] != 0:
		return '''
	'''+thread_name+''' = threading.Thread(target= '''+target_name+''', daemon = False, args = ['''+function_args3+'''], kwargs='''+kwargs_dict2+''')
	invoker_dict = {'invoked_du':'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': [''], 'kwargs': {}}}
	launch = False
	while launch == False:
		live_threads = invoker(invoker_dict)
		if live_threads % '''+str(config_dict["max_threads"])+''' != 0:
			'''+thread_name+'''.start()
			launch = True
	return json.dumps("cloudbook: thread launched")
'''
	else:
		return '''
	'''+thread_name+''' = threading.Thread(target= '''+target_name+''', daemon = False, args = ['''+function_args3+'''], kwargs='''+kwargs_dict2+''')
	'''+thread_name+'''.start()
	return json.dumps("cloudbook: thread launched")
'''

def global_def_fun(config_dict,function):
	function_name = config_dict["function_translated"][function]
	global_var_name = function[function.rfind(".")+1:]
	file = function[:function.rfind(".")]
	for i in config_dict["program_index"][file]:
		for j in config_dict["program_index"][file][i]:
			if j["type"] == 'global' and j["name"] == global_var_name:
				global_var_value = j["value"]

	global_var_attr = function_name+"."+global_var_name
	global_var_version = function_name+".ver_"+global_var_name
	global_var_lock = function_name +".lock_"+global_var_name

	return '''
def '''+function_name+'''(old_ver, op, *args, index=[]):
	if not hasattr('''+function_name+''', '''+'"'+global_var_name+'"'+'''):
		'''+function_name+"."+global_var_name+''' = '''+global_var_value+'''
	if not hasattr('''+function_name+''', "ver_'''+global_var_name+'"'+'''):
		'''+function_name+".ver_"+global_var_name+''' = 1
	if not hasattr('''+function_name+''', "lock_'''+global_var_name+'"'+'''):
		'''+ function_name +".lock_"+global_var_name+''' = threading.Lock()
	if op == "None":
		if old_ver == '''+function_name+".ver_"+global_var_name+''':
			return json.dumps(("None",old_ver))
		else:
			try:
				return json.dumps(('''+function_name+"."+global_var_name+","+function_name+".ver_"+global_var_name+'''))
			except:
				return json.dumps((str('''+function_name+"."+global_var_name+") ,"+function_name+".ver_"+global_var_name+'''))
	else:
		new_args = []
		for i in args:
			if isinstance(i,str):
				new_args.append("'"+i+"'")
			else:
				new_args.append(str(i))
		for i in index:
			if isinstance(i,str):
				op = "['"+i+"']" + op
			else:
				op = "["+str(i)+"]" + op
		if "=" in op:
			op = "'''+global_var_attr+'''"+op+new_args[0] #only 1 value in global_var = something
		else:
			op = "'''+global_var_attr+'''"+op+"("
			for i in new_args:
				op = op+i+","
			op = op + ")"
		try:
			'''+function_name+".ver_"+global_var_name+''' += 1
			return json.dumps((eval(op),'''+function_name+".ver_"+global_var_name+'''))
		except:
			with '''+function_name+".lock_"+global_var_name+''':
				exec(op)
				'''+function_name+".ver_"+global_var_name+''' += 1
			return json.dumps(("done",'''+function_name+".ver_"+global_var_name+'''))
	return json.dumps('cloudbook: done') 
'''

def du0_thread_counter(config_dict):
	#TODO crear un semaforo para cada función paralela
	return '''
def thread_counter(value):
	if not hasattr(thread_counter, "val"):
		thread_counter.val = 0
	if not hasattr(thread_counter, "cerrojo"):
		thread_counter.cerrojo = threading.Lock()
	if value == "++":
		with thread_counter.cerrojo:
			thread_counter.val += 1
	if value == "--":
		with thread_counter.cerrojo:
			thread_counter.val -= 1
	return json.dumps(thread_counter.val)

'''
def du0_critical_section_control_old():
	return '''
def critical_section_control(op):
	if (not hasattr(critical_section_control, 'value')):
		critical_section_control.value = "unlocked"
	if (not hasattr(critical_section_control, 'lock')):
		critical_section_control.lock = threading.Lock()
	with critical_section_control.lock:
		if critical_section_control.value == "unlocked":
			critical_section_control.value = "locked"
			return json.dumps("unlocked")
	if op == 'lock':
		critical_section_control.value = "locked"
	if op == 'unlock':
		critical_section_control.value = "unlocked"
	return json.dumps(critical_section_control.value)
'''

def du0_critical_section_control():
	return '''
def critical_section_control(op):
	if (not hasattr(critical_section_control, 'value')):
		critical_section_control.value = "unlocked"
	if (not hasattr(critical_section_control, 'lock')):
		critical_section_control.lock = threading.Lock()
	with critical_section_control.lock:
		if op == 'lock':
			if critical_section_control.value == "unlocked":
				critical_section_control.value = "locked"
				return json.dumps("unlocked")
			else:
				critical_section_control.value = "locked"
		if op == 'unlock':
			critical_section_control.value = "unlocked"
	return json.dumps(critical_section_control.value)
'''

def cloudbook_sync_code(config_dict):
	to_write = "invoker({'invoked_du': 'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': ['++'], 'kwargs': {}}})\n"
	return'''
def CLOUDBOOK_SYNC(t=None):
	invoker_dict = {'invoked_du':'du_0', 'invoked_function': 'thread_counter', 'invoker_function': 'thread_counter', 'params': {'args': [''], 'kwargs': {}}}
	#value = json.loads(invoker(invoker_dict))
	value = invoker(invoker_dict)
	temp = 0
	timeout = True
	if t != None:
		while value > 0 and timeout:
			if temp>t:
				#thread failure
				timeout = False
			time.sleep(0.01)
			temp+=1
			value = invoker(invoker_dict)
	else:
		while value>0:
			time.sleep(0.01)
			value = invoker(invoker_dict)
'''
def cloudbook_critical_section_code():
	return '''
def CLOUDBOOK_LOCK():
	lock_dict = {'invoked_du':'du_0', 'invoked_function': 'critical_section_control', 'invoker_function': 'critical_section_control', 'params': {'args': ['lock'], 'kwargs': {}}}
	value = invoker(lock_dict)
	#print("value:",value)
	while value != "unlocked":
		#print("no entro")
		value = invoker(lock_dict)
		time.sleep(0.1)

def CLOUDBOOK_UNLOCK():
	unlock_dict = {'invoked_du':'du_0', 'invoked_function': 'critical_section_control', 'invoker_function': 'critical_section_control', 'params': {'args': ['unlock'], 'kwargs': {}}}
	invoker(unlock_dict)

'''

def remove_unused_imports(config_dict):
	logging.debug(">>>Enter in remove used imports")
	program_files = config_dict["program_files"]
	folders = []
	files = []
	to_delete = []
	aux_config_dict = copy.deepcopy(config_dict["imports"])
	for i in config_dict["program_files"]:
		folders.append(i.replace("./",""))
		for j in config_dict["program_files"][i]:
			files.append(j.replace(".py",""))
	folders.remove('')
	##print("FOLDERS:",folders," FILES:",files)
	for file in aux_config_dict:
		logging.debug("	For file %s",file)
		logging.debug("	The imports are %s",aux_config_dict[file])
		for import_object in aux_config_dict[file]:
			logging.debug("		Import_object: %s", import_object)
			if import_object["type"] == 'import':
				name_import = import_object["name"]
				if (name_import in folders) or (name_import in files):
					to_delete.append(import_object)
					logging.debug("			To delete %s",import_object)
					config_dict["imports"][file].remove(import_object)
			if import_object["type"] == 'fromimport':
				name_import = import_object["name"]
				module_import = import_object["module"]
				if (name_import in folders) or (name_import in files) or (module_import in folders) or (module_import in files):
					to_delete.append(import_object)
					logging.debug("			To delete %s",import_object)
					config_dict["imports"][file].remove(import_object)

def flatten(x):
	result = []
	for el in x:
		if hasattr(el, "__iter__") and not isinstance(el, str):
			result.extend(flatten(el))
		else:
			result.append(el)
	return result

def noblocking_invocations_thread_launcher(config_dict, file):
	logging.debug(">>> Writting nonblocking invocations")
	for function in config_dict["nonblocking_invocations"]:
		for invocation in config_dict["nonblocking_invocations"][function]:
			function_name = config_dict["program_data"]["functions"][function].name
			function_args = astunparse.unparse(config_dict["program_data"]["functions"][function].args).replace("\n","")
			function_args_node = config_dict["program_data"]["functions"][function].args
			function_def = "\ndef "+invocation+"("+function_args+"):"
			function_body = function_body_text(config_dict,function_name, function_args, function_args_node, "nonblocking_inv")
			file.write(function_def+function_body)
	#escribo la funcion con nombre normal

def noblocking_invocations_target_code(config_dict,file):
	logging.debug(">>> Writting nonblocking target_code")
	for function in config_dict["nonblocking_invocations"]:
		#new_function = config_dict["program_data"]["functions"][function]
		new_function = config_dict["nonblocking_inv_nodes"][function]
		new_function.name = "nonblocking_inv_"+ config_dict["program_data"]["functions"][function].name
		file.write(astunparse.unparse(new_function))