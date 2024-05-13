import random

def randomise():
    # Create array of dimensions (x,y) with random numbers between (-1,1)
    return random.random()

def calculateProportionA(liquidA, liquidB):
    return (liquidA/(liquidA + liquidB)) * 100

def newLiquids(liquid, delta,  alpha):
    return liquid + (delta * alpha * randomise())

def protoOptimiser(desiredPeak, maxIterations, alpha, threshold):
    betterDelta = False
    liquidA = 5
    liquidB = 5
    previousLiquid = 'A'
    previousDelta = 0
    iterations = 0
    delta = 10000
    while iterations != maxIterations and delta > threshold:
        actualPeak = int(input("What was the actual peak?"))
        delta = abs(desiredPeak - actualPeak)
        if delta > previousDelta:
            switch = True
        else:
            switch = False

        if switch:
            if previousLiquid == 'A':
                liquidB = newLiquids(liquidB, delta, alpha)
                previousLiquid = 'B'
            elif previousLiquid == 'B':
                liquidA = newLiquids(liquidA, delta, alpha)
                previousLiquid = 'A'
        else:
            if previousLiquid == 'A':
                liquidA = newLiquids(liquidA, delta, alpha)
                previousLiquid = 'A'
            elif previousLiquid == 'B':
                liquidB = newLiquids(liquidB, delta, alpha)
                previousLiquid = 'B'

        proportionA = calculateProportionA(liquidA, liquidB)
        proportionB = 100 - calculateProportionA(liquidA, liquidB)

        print("Try Liquid A = ", liquidA, " (", proportionA, "%) and Liquid B = ", liquidB, " (", proportionB, "%)")

        previousDelta = delta




desiredPeak = int(input("Enter desired wavelength peak"))
alpha = 0.05
maxIterations = 100
threshold = 10
protoOptimiser(desiredPeak, maxIterations, alpha, threshold)
print(randomise())