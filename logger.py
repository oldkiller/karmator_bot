import logging

logging.basicConfig(
	format=("%(filename)s [Line:%(lineno)d]# " +
			"%(levelname)-8s [%(asctime)s] %(message)s"),
	level=logging.INFO)

db_log = logging.getLogger("db_log")
main_log = logging.getLogger("main_log")