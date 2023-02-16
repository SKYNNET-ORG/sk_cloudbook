import logging
import os
import json
from pprint import pformat
from . import matrix_builder
from . import get_pragmas

from . import matrix_filler
from . import matrix_cleaner

def graph_builder(config_dict):
	'''The graph builder is in charge of obtaining the files of which the program is composed, 
obtaining the functions, the labels and the global variables to return the empty summons matrix'''
	logging.debug(">>>Enter in graph builder")
	indent_log(config_dict["log_file_handler"],2)
	#Matrix_builder: Get files
	program_files = matrix_builder.file_scanner(config_dict)
	config_dict["program_files"] = program_files
	#Matrix_builder: Get functions, also pragmas
	matrix_builder.get_program_info(config_dict)
	get_pragmas.get_pragmas(config_dict)
	get_pragmas.get_globals(config_dict)
	#Get function list
	matrix_builder.get_function_list(config_dict)
	indent_log(config_dict["log_file_handler"],1)
	log_results_builder(config_dict)
	logging.debug("<<<Exit from graph builder")
	logging.debug("=======================================\n")
	return config_dict

def graph_filler(config_dict):
	logging.debug(">>>Enter in graph filler")
	indent_log(config_dict["log_file_handler"],2)
	matrix_filler.get_invocations(config_dict)
	log_results_filler(config_dict)
	matrix_cleaner.clean_matrix(config_dict)
	indent_log(config_dict["log_file_handler"],1)
	log_results_filler(config_dict)
	#Save collapsed matrix
	matrix_str = json.dumps(config_dict["matrix"])
	out_route =  config_dict["distributed_dir"] + os.sep + "matrix" + os.sep + "matrix.json"
	file = open(out_route,"w")
	file.write(matrix_str)
	file.close()
	logging.debug(">>>Exit in graph filler")
	logging.debug("=======================================\n")
	return config_dict

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

def log_program_index(config_dict):
	for file in config_dict['program_index']:
		logging.info("In file: %s",file)
		for nline in config_dict['program_index'][file]:
			logging.info("	%s:	%s",nline,config_dict['program_index'][file][nline])

def log_results_builder(config_dict):
	logging.info("Graph Builder Results:")
	logging.info("======================")
	logging.info("Program files 	 	  :	%s",config_dict["program_files"])
	logging.info("Function list 		  :	%s",config_dict["function_list"])
	logging.info("Class list 	 		  :   	%s",config_dict["class_list"])
	logging.info("Pragmas 				  :      	%s",config_dict["pragmas"])
	logging.info("Global_vars 			  :	%s",config_dict["global_vars"])
	logging.info("Imports      			  :	%s",config_dict["imports"])
	logging.info("Nonblocking Invocations :	%s",config_dict["nonblocking_invocations"])
	logging.info("Max threads for all agents :	%s",config_dict["max_threads"])
	logging.info("Nonblocking Invocations nodes :	%s",config_dict["nonblocking_inv_nodes"])
	logging.info('Program_index:')
	log_program_index(config_dict)

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