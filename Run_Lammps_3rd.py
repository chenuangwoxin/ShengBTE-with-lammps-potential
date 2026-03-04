"""
reated on Tue May 17 21:31:08 2016

@author: Zhongwei Zhang

Modified by Jingchao Zhang
"""

from ase.io import read, write
import numpy as np
import glob
import os
import sys

# 1. 搜寻并排序位移文件
poscar_list = glob.glob("3RD.POSCAR.*")
if not poscar_list:
    print("Error: No files matching '3RD.POSCAR.*' found!")
    sys.exit()

# 按数字后缀排序
list.sort(poscar_list, key=lambda x: int(x.split('3RD.POSCAR.')[1]))
nposcar = len(poscar_list)

for i in range(nposcar):
    name_poscar = poscar_list[i]
    tail = name_poscar.split('3RD.POSCAR.')[1]
    print(f"Processing: {name_poscar}")

    # --- 使用 ASE 替代 AWK 和手动解析 ---
    # 读取 VASP 结构
    atoms = read(name_poscar, format='vasp')

    # 写入 LAMMPS data 文件 (ASE 会处理所有的坐标转换)
    # atom_style 默认通常为 'atomic'，如果需要电荷可以改为 'full'
    atoms.write('data.lmp', format='lammps-data',atom_style='charge')

    # 获取原子信息
    num = len(atoms)
    # 获取元素种类数量
    ntypes = len(set(atoms.get_chemical_symbols()))

    # --- 调用 LAMMPS 计算 ---
    # 确保目录下有 in.force 文件，且 in.force 中 read_data 读的是 data.lmp
    os.system("lmp < in.force > out")

    # --- 提取受力并生成 vasprun.xml ---
    if not os.path.exists("dump.frc"):
        print(f"Error: dump.frc not found for {name_poscar}")
        continue

    with open("dump.frc", 'r') as f_dump:
        data_dump = f_dump.readlines()

    name_xml = f'vasprun.xml-{tail}'

    with open(name_xml, 'w') as f_vasp:
        f_vasp.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        f_vasp.write('<modeling>\n')
        f_vasp.write(' <generator>\n')
        f_vasp.write('  <i name="version" type="string">5.4.1  </i>\n')
        f_vasp.write(' </generator>\n')
        f_vasp.write(' <atominfo>\n')
        f_vasp.write(f'  <atoms>{num}</atoms>\n')
        f_vasp.write(f'  <types>       {ntypes} </types>\n')
        f_vasp.write(' </atominfo>\n')
        f_vasp.write(' <calculation>\n')
        f_vasp.write('  <varray name="forces" >\n')

        # 假设 dump.frc 从第10行(索引9)开始是原子受力数据 (ID fx fy fz)
        # ！！！注意：LAMMPS 导出 dump 时务必加上 dump_modify sort id ！！！
        for n in range(num):
            cols = data_dump[9+n].split()
            # 索引 [1],[2],[3] 分别对应 fx, fy, fz
            f_vasp.write(f'   <v> {cols[1]} {cols[2]} {cols[3]} </v>\n')

        f_vasp.write('  </varray>\n')
        f_vasp.write(' </calculation>\n')
        f_vasp.write('</modeling>\n')

    # --- 创建目录并移动文件 ---
    job_dir = f"job-{tail}"
    if not os.path.exists(job_dir):
        os.makedirs(job_dir)

    os.rename(name_xml, os.path.join(job_dir, "vasprun.xml"))

print("Successfully completed all structures.")
