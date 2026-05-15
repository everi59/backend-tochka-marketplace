try:
	import app.main
	print("ok, title:", app.main.app.title)
except Exception as e:
	import traceback, sys
	traceback.print_exc()
