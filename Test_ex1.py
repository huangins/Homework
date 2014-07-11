from ex1 import febonacci 
def test_febonacci():
	for i in range(0, 50):
		if i < 2:
			assert febonacci(0) == 1
		assert febonacci(2) == 3