from . import collapser_llcsb
from . import collapser_ll
import logging

def get_collapser(criteria):
	logging.debug("	>>>Getting collapser")
	if (criteria == 0):
	# For the moment there is only one collapser to choose
	# low latency & code Size balanced
		logging.debug("		Low latency & code size balanced collapser selected")
		return collapser_llcsb.choose_functions_to_collapse
	else :
		logging.debug("		Low latency collapser selected")
		return collapser_ll.choose_functions_to_collapse
