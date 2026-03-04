# -*- coding: utf-8 -*-
"""
Created on Tue May 17 21:31:08 2016

@author: Zhongwei Zhang

Modified by Jingchao Zhang 2026-3-3
"""
from ase.io import read
import glob
import os
import sys

# 1. 搜寻位移文件
poscar_list = glob.glob("POSCAR-*")
if not poscar_list:
    print("Error: No POSCAR-* files found!")
    sys.exit()

list.sort(poscar_list, key=lambda x: int(x.split('POSCAR-')[1]))
nposcar = len(poscar_list)

print(f"Found {nposcar} displacement files. Starting calculation...")

for i in range(nposcar):
    name_poscar = poscar_list[i]
    tail = name_poscar.split('POSCAR-')[1]
    print(f"Processing: {name_poscar}")

    # 读取原始结构
    atoms_orig = read(name_poscar, format='vasp')
    num = len(atoms_orig)
    ntype = len(set(atoms_orig.get_chemical_symbols()))

    # --- 最关键的修改：获取 分数坐标 (Scaled/Fractional positions) ---
    orig_scaled_positions = atoms_orig.get_scaled_positions()
    orig_cell = atoms_orig.get_cell()

    # 转换为 LAMMPS data
    atoms_orig.write('data.lmp', format='lammps-data', atom_style="charge")

    # 2. 调用 LAMMPS 计算受力
    os.system("lmp < in.force > out")

    # 3. 提取受力
    if not os.path.exists("dump.frc"):
        print(f"Error: dump.frc not found for {name_poscar}")
        continue

    with open("dump.frc", 'r') as f_dump:
        data_dump = f_dump.readlines()

    name_vasp = f'vasprun.xml-{tail}'

    # 4. 生成 vasprun.xml
    with open(name_vasp, 'w') as f_xml:
        f_xml.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        f_xml.write('<modeling>\n')
        f_xml.write(' <generator>\n')
        f_xml.write('  <i name="version" type="string">5.4.1  </i>\n')
        f_xml.write(' </generator>\n')
        f_xml.write(' <atominfo>\n')
        f_xml.write(f'  <atoms>{num}</atoms>\n')
        f_xml.write(f'  <types>       {ntype} </types>\n')
        f_xml.write(' </atominfo>\n')

        # 写入晶格信息
        f_xml.write(' <structure>\n')
        f_xml.write('  <crystal>\n')
        f_xml.write('   <varray name="basis" >\n')
        for vec in orig_cell:
            f_xml.write(f'    <v> {vec[0]:.12f} {vec[1]:.12f} {vec[2]:.12f} </v>\n')
        f_xml.write('   </varray>\n')
        f_xml.write('  </crystal>\n')

        # 写入 分数坐标 (Phonopy 严格检查的就是这个)
        f_xml.write('  <varray name="positions" >\n')
        for pos in orig_scaled_positions:
            f_xml.write(f'   <v> {pos[0]:.12f} {pos[1]:.12f} {pos[2]:.12f} </v>\n')
        f_xml.write('  </varray>\n')
        f_xml.write(' </structure>\n')

        f_xml.write(' <calculation>\n')
        # 写入能量
        f_xml.write('  <energy>\n')
        f_xml.write('   <i name="e_fr_energy">      0.00000000</i>\n')
        f_xml.write('   <i name="e_wo_entrp">      0.00000000</i>\n')
        f_xml.write('   <i name="e_0_energy">      0.00000000</i>\n')
        f_xml.write('  </energy>\n')

        # 写入受力
        f_xml.write('  <varray name="forces" >\n')
        for n in range(num):
            cols = data_dump[9+n].split()
            f_xml.write(f'   <v> {cols[1]} {cols[2]} {cols[3]} </v>\n')
        f_xml.write('  </varray>\n')
        f_xml.write(' </calculation>\n')
        f_xml.write('</modeling>\n')

# 5. 后处理
print("All forces calculated. Running Phonopy to collect data...")
if os.path.exists("FORCE_SETS"):
    os.remove("FORCE_SETS")
os.system("phonopy -f vasprun.xml-*")
print("Done! FORCE_SETS has been generated.")
