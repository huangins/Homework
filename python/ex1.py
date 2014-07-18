input = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
list = ["", "", ""]
for i in range(0, len(input)):
	for j in range(0, 3):
		if i%3 == j:
			list[j] += input[i]
			break
print list