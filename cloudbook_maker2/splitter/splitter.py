import logging
import os
import sys
import json

from . import iterator
from . import translator
from . import du_creator

def indent_log(fh, level):
	filehandler = fh
	if level==0:
		formatter = logging.Formatter('%(message)s')
	if level==1:
		formatter = logging.Formatter('	%(message)s')
	if level==2:
		formatter = logging.Formatter('		%(message)s')
	if level==3:
		formatter = logging.Formatter('			%(message)s')
	filehandler.setFormatter(formatter)
	log = logging.getLogger()  # root logger - Good to get it only once.
	for hdlr in log.handlers[:]:  # remove the existing file handlers
	    if isinstance(hdlr,logging.FileHandler):
	        log.removeHandler(hdlr)
	log.addHandler(filehandler)      # set the new handler

def split_program(config_dict):
	indent_log(config_dict["log_file_handler"],0)
	logging.debug(">>>Enter in split program")
	indent_log(config_dict["log_file_handler"],1)
	##iterator.iterate(config_dict)
	if config_dict["input_matrix"] != "":
		original_matrix_str = json.dumps(config_dict["matrix"])
		config_dict["matrix"] = config_dict["input_matrix"]
		#Rename original matrix
		new_route =  config_dict["distributed_dir"] + os.sep + "matrix" + os.sep + "original_matrix.json"
		file = open(new_route,"w")
		file.write(original_matrix_str)
		file.close()
		#Save collapsed matrix
		matrix_str = json.dumps(config_dict["matrix"])
		out_route =  config_dict["distributed_dir"] + os.sep + "matrix" + os.sep + "matrix.json"
		file = open(out_route,"w")
		file.write(matrix_str)
		file.close()
	iterator.iterate(config_dict)
	log_results_filler(config_dict)
	#Save collapsed matrix
	##out_route =  config_dict["distributed_dir"] + os.sep + "matrix" + os.sep + "matrix.json"
	##file = open(out_route,"w")
	##file.write(str(config_dict["matrix"]))
	##file.close()	
	#Once collapsed, generate dus
	#dus normales
	get_initial_dus(config_dict)
	#dus tras aplicar etiquetas
	get_final_dus(config_dict)
	#translate functions
	translate_function_names(config_dict)
	#update function names in progrma
	translator.tranlateInvocations(config_dict)
	translator.translateFunctionNames(config_dict)
	translator.translateReturns(config_dict)
	translator.add_thread_counter_minus(config_dict)
	#write nonblocking invocations
	translator.add_nonblocking_inv(config_dict)
	#create nonblocking invocation functions
	translator.translate_nonblocking_functions(config_dict)
	#write the dus
	#por cada du, miro imports (meto todos menos los de la antigua forma), miro cada funcion
	#veo si hay etiquetas y trato las invocaciones
	#en la du_0 meto el main
	for i in config_dict["dus"]:
		du_creator.create_du(i, config_dict)

def get_initial_dus(config_dict):
	logging.debug(">>>Enter in get initial dus")
	matrix = config_dict["matrix"]
	if config_dict["pragmas"]["main"] == []:
		logging.error("Error: No main pragma")
		sys.exit("\nError: No main pragma in original source code")
	for num,i in enumerate(matrix[0]):
		num_du = num
		if i is matrix[0][0]:
			continue
		if config_dict["pragmas"]["main"] in matrix[0][num]: #make du_0 the one with the main function
			#TODO if there is not Cloudbook:main pragma, here is catched
			num_du = 0
		if isinstance(matrix[0][num],str):
			config_dict["dus"]["du_"+str(num_du)] = list(matrix[0][num].split())
		elif isinstance(matrix[0][num],list):
			config_dict["dus"]["du_"+str(num_du)] = matrix[0][num]
		else: #TODO lanzar mejor la excepcion por si acaso https://stackoverflow.com/questions/2052390/manually-raising-throwing-an-exception-in-python
			logging.error("Error: The format of the functions from de du: %s, is invalid",matrix[0][num])
			#raise Exception("Error: The format of the functions from de du, is invalid")
	logging.debug("	Dus:")
	for du in config_dict["dus"]:
		logging.debug("		%s:%s",du,config_dict["dus"][du])
	logging.debug("=======================")
	logging.debug("<<<Exit from get initial dus")

def get_final_dus(config_dict):
	logging.debug(">>>Enter in get final dus")
	non_reliable_mode = config_dict["non-reliable_agent_mode"]
	du0_functions = config_dict["pragmas"]["du0_functions"]
	parallel_functions = config_dict["pragmas"]["parallel"]
	recursive_functions = config_dict["pragmas"]["recursive"]
	local_functions = config_dict["pragmas"]["local"]
	nonblocking_functions = config_dict["pragmas"]["nonblocking_def"]
	main = config_dict["pragmas"]["main"]
	dus = config_dict["dus"]
	
	logging.debug("	Non reliable agent mode:	%s",non_reliable_mode)
	logging.debug("	Du_0 Functions:         	%s",du0_functions)
	logging.debug("	Parallel functions:     	%s",parallel_functions)
	logging.debug("	Recursive functions:	    %s",recursive_functions)
	logging.debug("	Local functions:	        %s",local_functions)
	logging.debug("	Nonblocking functions:	    %s",nonblocking_functions)
	logging.debug("	Main function:	            %s",main)

	if not non_reliable_mode:
		final_dus = dus
	else:
		final_dus = {"du_0":[],"du_default":[]}
		for du in dus: #put all functions in du_0
			final_dus["du_0"] += dus[du]

	functions_to_remove = parallel_functions + recursive_functions + nonblocking_functions
	functions_to_append = local_functions
	functions_to_append_0 = du0_functions
	for du in final_dus:
		if du == "du_0": #meto las du_functions
			final_dus["du_0"] += functions_to_append_0
			final_dus["du_0"] = [f for f in final_dus["du_0"] if f not in functions_to_remove]
			final_dus["du_0"].append(main)
		else:
			final_dus[du] = [f for f in final_dus[du] if f not in functions_to_remove]
		final_dus[du] += functions_to_append
		final_dus[du] = list(set(final_dus[du])) #remove duplicates
	final_dus["du_default"] = functions_to_remove + functions_to_append
	config_dict["dus"] = final_dus
	#create critical_dus
	for du in final_dus:
		for fun in final_dus[du]:
			aux_fun = fun[fun.rfind(".")+1:]
			##print("AUXFUN:", aux_fun)
			if aux_fun in config_dict["global_vars"]["global"]:# + config_dict["global_vars"]["safe"]:
				config_dict["critical_dus"].append(du)
	config_dict["critical_dus"] = list(set(config_dict["critical_dus"]))
	#SKYNNET Quitar funciones de dus, que ya esten en la du0, las funciones du0 no deberian tener replicas
	logging.debug(config_dict["dus"])
	for du in config_dict["dus"]:
		for fun in config_dict["dus"][du]:
			if fun in du0_functions and du != 'du_0':
				logging.debug(fun)
				config_dict["dus"][du].remove(fun)
	logging.debug("	Dus:")
	for du in config_dict["dus"]:
		logging.debug("		%s:%s",du,config_dict["dus"][du])
	logging.debug("	Critical dus:	%s",config_dict["critical_dus"])
	logging.debug("<<<Exit from get final dus")
	logging.debug("=======================")

def translate_function_names(config_dict):
	logging.debug(">>>Enter in translate function names")
	for num,function in enumerate(config_dict["function_list"]):
		config_dict["function_translated"][function] = "f"+str(num)
		logging.debug("	%s is %s",function,config_dict["function_translated"][function])
	logging.debug(">>>Exit from translate function names")
	logging.debug("=======================")

def log_results_filler(config_dict):
	logging.info("Graph Filler Results:")
	logging.info("======================")
	logging.info("Clean matrix:")
	indent_log(config_dict["log_file_handler"],0)
	matrix = config_dict["matrix"]
	s = [[str(e) for e in row] for row in matrix]
	lens = [max(map(len, col)) for col in zip(*s)]
	fmt = '\t'.join('{{:{}}}'.format(x) for x in lens)
	table = [fmt.format(*row) for row in s]
	logging.info('\n'.join(table))
	indent_log(config_dict["log_file_handler"],1)