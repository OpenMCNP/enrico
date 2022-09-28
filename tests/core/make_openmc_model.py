import argparse
from math import pi

import numpy as np
import openmc


# Basic model parameters
fuel_or = 0.406
clad_ir = 0.414
clad_or = 0.475
pitch = 1.26
fuel_length = 10.0

# Create materials
uo2_density = 10.97
percent_td = 0.96
uo2 = openmc.Material(name='UO2')
uo2.add_element('U', 1.0, enrichment=4.95)
uo2.add_element('O', 2.0)
uo2.set_density('g/cm3', uo2_density*percent_td)

m5_niobium = 0.01    # http://publications.jrc.ec.europa.eu/repository/bitstream/JRC100644/lcna28366enn.pdf
m5_oxygen = 0.00135  # http://publications.jrc.ec.europa.eu/repository/bitstream/JRC100644/lcna28366enn.pdf
m5_density = 6.494   # 10.1039/C5DT03403E
m5 = openmc.Material(name='M5')
m5.add_element('Zr', 1.0 - m5_niobium - m5_oxygen)
m5.add_element('Nb', m5_niobium)
m5.add_element('O', m5_oxygen)
m5.set_density('g/cm3', m5_density)

# NuScale DCA, Ch. 4, Table 4.1-1
psia = 0.0068947572931683625  # MPa
system_pressure = 1850*psia
core_avg_temperature = (543 - 32)*5/9 + 273.15  # K
water_density = openmc.data.water_density(core_avg_temperature, system_pressure)
water = openmc.Material(name='Water')
water.add_nuclide('H1', 2.0)
water.add_element('O', 1.0)
water.add_s_alpha_beta('c_H_in_H2O')
water.set_density('g/cm3', water_density)

# Create cylinders
fuel_outer = openmc.ZCylinder(r=fuel_or)
clad_inner = openmc.ZCylinder(r=clad_ir)
clad_outer = openmc.ZCylinder(r=clad_or)

# make pin
pin = openmc.model.pin([fuel_outer, clad_inner, clad_outer], [uo2, None, m5, water])

# make assembly lattice
assem_lat = openmc.RectLattice()
assem_lat.lower_left = (-pitch, -pitch, 0.0)
assem_lat.pitch = (pitch*2, pitch*2, fuel_length)
assem_lat.universes = np.full((1, 2, 2), pin)

# make assembly
assembly_region = openmc.rectangular_prism(pitch * 2, pitch * 2, origin=(0, 0, fuel_length/2.0), boundary_type='transmission')
assembly_cell = openmc.Cell(fill=assem_lat, region=assembly_region)
assembly = openmc.Universe(cells=[assembly_cell])

# make core lattice
assem_pitch = pitch * 2
core_lat = openmc.RectLattice()
core_lat.lower_left = (-assem_pitch, -assem_pitch, 0.0)
core_lat.pitch = (assem_pitch, assem_pitch, fuel_length)
core_lat.universes = np.full((1, 3, 3), assembly)

# make core
core_region = openmc.rectangular_prism(assem_pitch, assem_pitch, origin=(0, 0, fuel_length/2.0), boundary_type='transmission')
print(core_region.get_surfaces())
core = openmc.Cell(fill=core_lat, region=core_region)

model = openmc.model.Model()
model.geometry = openmc.Geometry([core])

model.settings.particles = 1000
model.settings.inactive = 10
model.settings.batches = 50
model.settings.source = openmc.Source(
    space=openmc.stats.Box(
        (-assem_pitch*3/2., -assem_pitch*3/2., 0.0),
        (assem_pitch*3/2., assem_pitch*3/2., fuel_length),
        True
    )
)
model.settings.temperature = {
    'default': 523.15,
    'method': 'interpolation',
    'range': (300.0, 1500.0),
    'multipole': True
}

model.export_to_xml()
