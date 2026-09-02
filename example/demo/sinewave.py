from ifigure.interactive import figure
import numpy as np

# Generate sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

v = figure(size=(500, 400))  # Create viewer 500x4oo pixel
v.plot(x, y)
v.title("Sine Wave")
v.xlabel("x-axis")
v.ylabel("y-axis")
v.legend('curve1')
v.savefig("sine_wave.pdf") # Save the plot as a PDF



