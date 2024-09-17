#!/usr/bin/python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

def triangular(x, points):
    """Triangular membership function."""
    if x <= points[0][0] or x >= points[2][0]:
        return 0.0
    elif points[0][0] < x <= points[1][0]:
        return (x - points[0][0]) / (points[1][0] - points[0][0])
    else:
        return (points[2][0] - x) / (points[2][0] - points[1][0])

def plot_membership_function(x, low_points, medium_points, high_points, variable_name, save_name):
    """Plot membership function."""
    low_mf = [triangular(i, low_points) for i in x]
    medium_mf = [triangular(i, medium_points) for i in x]
    high_mf = [triangular(i, high_points) for i in x]

    plt.figure(figsize=(4, 3))  
    plt.plot(x, low_mf, label='LOW', color='blue', linewidth=width)
    plt.plot(x, medium_mf, label='MEDIUM', color='orange', linewidth=width)
    plt.plot(x, high_mf, label='HIGH', color='red', linewidth=width) 
    plt.xlabel(variable_name, fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.ylabel('Membership', fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.xticks(fontsize=tamFonteGraf, fontname=nomeFonte)
    plt.yticks(fontsize=tamFonteGraf, fontname=nomeFonte)

    legend_font = FontProperties(family=nomeFonte, style='normal', size=tamFonteGraf)
    plt.legend(prop=legend_font, bbox_to_anchor=(0.5, 1.4), loc='upper center', columnspacing=1.0, handlelength=1.0, frameon=False, ncol=4)

    plt.ylim(0, 1)
    plt.xlim(min(x), max(x))
    plt.tight_layout()    

    if save_name:
        plt.savefig(save_name)
    else:
        plt.show()

def main():
    """Main function."""
    global width, tamFonteGraf, nomeFonte
    
    width = 6.0
    tamFonteGraf = 16
    nomeFonte = 'Times New Roman'   # def: "sans-serif"  #"Arial" #'Times New Roman' 
    
    x_snr = np.linspace(0, 1, 1000)
    x_sf = np.linspace(7, 12, 1000)
    x_tp = np.linspace(2, 14, 1000)

    # Defining the fuzzy membership function vertices for SNR
    low_snr = [(0.0, 0.0), (0.0, 1.0), (0.5, 0.0)]
    medium_snr = [(0.4, 0.0), (0.6, 1.0), (0.8, 0.0)]
    high_snr = [(0.7, 0.0), (1.0, 1.0), (1.0, 0.0)]

    # Defining the fuzzy membership function vertices for SF
    low_sf = [(7.0, 0.0), (7.0, 1.0), (9.0, 0.0)]
    medium_sf = [(8.0, 0.0), (9.5, 1.0), (11.0, 0.0)]
    high_sf = [(10.0, 0.0), (11.0, 1.0), (12.0, 0.0)]
    
    # Defining the fuzzy membership function vertices for TP
    low_tp = [(2.0, 0.0), (4.0, 1.0), (6.0, 0.0)]
    medium_tp = [(5.0, 0.0), (8.0, 1.0), (11.0, 0.0)]
    high_tp = [(10.0, 0.0), (14.0, 1.0), (14.0, 0.0)]

    plot_membership_function(x_snr, low_snr, medium_snr, high_snr, 'SNRmargin', 'fuzzyMF_SNR.png')
    plot_membership_function(x_sf, low_sf, medium_sf, high_sf, 'SF', 'fuzzyMF_SF.png')
    plot_membership_function(x_tp, low_tp, medium_tp, high_tp, 'TP', 'fuzzyMF_TP.png')

if __name__ == "__main__":
    main()
