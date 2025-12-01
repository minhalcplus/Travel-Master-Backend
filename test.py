import random
import string


def generate_otp_v2():
  # Generate 6 random digits and shuffle
  digits = random.choices(string.digits, k=6)
  random.shuffle(digits)
  return ''.join(digits)
print(generate_otp_v2())