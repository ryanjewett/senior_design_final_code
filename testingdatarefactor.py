import math

def normalize_xyz(x, y, z):
    magnitude = math.sqrt(x**2 + y**2 + z**2)
    return x / magnitude, y / magnitude, z / magnitude

# Example usage:
x, y, z = 0.3854665, -0.09097966, 12.10987
x_norm, y_norm, z_norm = normalize_xyz(x, y, z)
print(x_norm, y_norm, z_norm)