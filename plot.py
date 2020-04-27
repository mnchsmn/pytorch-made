import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import json

datasets = ['adult', 'connect4', 'dna', 'web']
models = ['_500#m1#s1.json','_500#m300#s300.json']


men_means, men_std = (20, 35, 30, 35, 27), (2, 3, 4, 1, 2)
women_means, women_std = (25, 32, 34, 20, 25), (3, 5, 2, 3, 3)

# set width of bar
barWidth = 0.2

me_1_mask = []
me_300_masks = []
for ds in datasets:
    with open('experiments/' + ds + '.npz/' + models[0]) as json_data:
        d = json.load(json_data)
        me_1_mask.append(d['test_loss'])
    with open('experiments/' + ds + '.npz/' + models[1]) as json_data:
        print(ds)
        d = json.load(json_data)
        me_300_masks.append(d['test_loss'])

them_1_mask = [13.12, 11.9, 83.63, 28.53]
them_300_masks = [13.13, 11.9, 79.66, 28.25]
 
# Set position of bar on X axis
r1 = np.arange(len(me_1_mask))
r2 = [x + barWidth for x in r1]
r3 = [x + barWidth for x in r2]
r4 = [x + barWidth for x in r3]
 
# Make the plot
plt.bar(r1, them_1_mask, color='#3498db', width=barWidth, edgecolor='white', label='MADE - 1 Mask')
plt.bar(r2, me_1_mask, color='#db7734', width=barWidth, edgecolor='white', label='Reproduced - 1 Mask')
plt.bar(r3, them_300_masks, color='#3498db', width=barWidth, edgecolor='white', label='MADE - 300 Masks', hatch='.')
plt.bar(r4, me_300_masks, color='#db7734', width=barWidth, edgecolor='white', label='Reproduced - 300 Masks', hatch='.')
 
# Add xticks on the middle of the group bars
plt.xlabel('group', fontweight='bold')
plt.xticks([r + barWidth for r in range(len(me_1_mask))], datasets)
 
# Create legend & Show graphic
plt.legend()
plt.savefig('foo.pdf')