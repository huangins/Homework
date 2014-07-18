from jinja2 import Template
from gmail import GMail, Message

mailingList = {'Ins1':'ins.huang+1@gmail.com','Ins2':'ins.huang+2@gmail.com'}

usr = GMail('ins.huang@gmail.com','xxxxx')

template = Template('Hello {{ name }}!\nYour email is {{ email }}\nThis is a junk mail.\nHave a nice day.')

for target in mailingList:
	context = template.render(name=target, email=mailingList[target])
	msg = Message(to=mailingList[target],text=context,subject="Junk mail")
	print context
	usr.send(msg)

usr.close()