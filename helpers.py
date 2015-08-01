from datetime import datetime, timedelta
from user import User
from action import Action

def serialize(var):
	if isinstance(var, User):
		return var.to_json()

	if isinstance(var, Action):
		return var.to_json()

	if isinstance(var, object):
		return var.__dict__
	else:
		return var

def within_one_week(timestamp):
	now = datetime.utcnow()
	week = timedelta(weeks=1)

	return timestamp + week >= now