import matplotlib.pyplot as plt
import math
import random

def erlang(x, k, lmb):
    sum = 0
    for n in range(k):
        sum += math.exp(-lmb*x) * (lmb*x)**n / math.factorial(n)
    return 1-sum

# k = shape
# lmb = rate

def fun(layer_skill1, layer_skill2, layer_ff1, layer_ff2):
    if layer_skill1 <= 10:
        layer_skill1 = int(round(layer_skill1*4.5))
    if layer_skill2 <= 10:
        layer_skill2 = int(round(layer_skill2*4.5))

    x = [0.1*i for i in range(10*max(layer_skill1, layer_skill2))]
    team1 = []; team2 = []

    max_layer_skill = max(layer_skill1, layer_skill2)
    print(math.ceil(layer_skill1 * erlang(random.random() * max_layer_skill, 2, 0.25)))
    print(math.ceil(layer_skill2 * erlang(random.random() * max_layer_skill, 2, 0.25)))

    for i in range(len(x)):
        team1.append((layer_skill1 + (layer_skill2-layer_skill1)/2.5) * erlang(x[i], 3, 0.25))

    for i in range(len(x)):
        team2.append((layer_skill2 + (layer_skill1-layer_skill2)/2.5) * erlang(x[i], 3, 0.25))

    plt.plot(x, team1, x, team2)
    plt.show()

fun(40, 35, 0, 0)