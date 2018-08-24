import os
from subprocess import getstatusoutput
import textwrap
from dataclasses import dataclass
import random
import string
import json
import math
from copy import deepcopy
import random as rand

def update_obj_from_dict_recursively(some_obj, some_dict):
	"""
	Useful to convert nested json files into nested dataclasses

	Example
	-------
	@dataclass
	class InputOptions:
		path: str = None
		n1: float = 0
		some_thing: Opt2 = Opt2()

	@dataclass
	class Opt2:
		some_string:str = None
		some_num:float = 0.0

	...

	input_dict_list = UI_load_json_file()

	...

	in_opt = InputOptions()
	update_obj_from_dict_recursively (in_opt, input_dict)

	:param some_obj:
	:param some_dict:
	:return:
	"""
	for k in some_dict:
		tmp_v = some_dict[k]
		if isinstance(tmp_v, dict):
			tmp_obj = some_obj.__dict__[k]
			update_obj_from_dict_recursively(tmp_obj, tmp_v)
		else:
			some_obj.__dict__.update({k:tmp_v})

def convert_obj_to_json_recursively(obj):

	# first check if obj has __dict__
	assert(hasattr(obj, '__dict__'))
	obj_dict = obj.__dict__

	json_str = '{'
	for ind,key in enumerate(obj_dict):
		if ind != 0:
			json_str+=','

		val = obj_dict[key]
		# if val is an object
		if (hasattr(val, '__dict__')):
			json_str +=  '"' + key+'":' + convert_obj_to_json_recursively(val)
		else:
			json_str += '"' + key+'":' + json.dumps(val)

	json_str += '}'
	return json_str

def outer_product_object_list(obj, start_ind = 0):
	# given an object which may contain some lists, return a list of objects that
	# holds individuals items of the list instead

	assert (hasattr(obj, '__dict__'))
	obj_dict = obj.__dict__
	dict_list = list(enumerate(obj_dict))

	for ind in range(start_ind, len(dict_list)):

		key = dict_list[ind][1]
		val = obj_dict[key]

		# if found an object
		if hasattr(val, '__dict__'):
			# lets open up this object and explore
			sub_obj = outer_product_object_list(val)
			# if it turns out that this object contain lists
			if isinstance(sub_obj, list):

				result = [None] * len(sub_obj)

				for (ind_i, val_i) in enumerate(sub_obj):
					obj_tmp = deepcopy(obj)
					setattr(obj_tmp, key, val_i)
					result[ind_i] = outer_product_object_list(obj_tmp, start_ind+1) #plus one here is impt

				return result

			# if the object does not contain any lists, don't bother with it
			else:
				pass


		# if found a list, stop and flatten list
		elif isinstance(val, list):

			result = [None]*len(val)

			for (ind_i, val_i) in enumerate(val):
				obj_tmp = deepcopy(obj)
				setattr(obj_tmp, key, val_i)
				result[ind_i] = outer_product_object_list(obj_tmp, start_ind+1) #do not open up list of list

			return  result

	return obj

def flatten(some_list):
	"""Given a list, possibly nested to any level, return it flattened."""
	new_list = []
	for item in some_list:
		if isinstance(item, list):
			new_list.extend(flatten(item))
		else:
			new_list.append(item)
	return new_list



def load_json_file(files):
	"""
	load input json file
	:return:
	"""
	# root = tk.Tk()
	# files = filedialog.askopenfilenames(title='Select json file')

	data_loaded = []

	if files == '':
		return data_loaded

	for file in files:
		converted_path = os.path.relpath(file)
		# if the user did selected something
		with open(converted_path) as data_file:
			data_loaded.append(json.load(data_file))

	return data_loaded



# simple helper classes
@dataclass
class Vector:
	x: float = 0
	y: float = 0
	z: float = 0

# material parameters
@dataclass
class MaterialParameters:
	landau_damping: float = 0.1
	mag_sat: float = 1 # magnetisation saturation in MA/m
	exchange: float = 10  # exchange in pJ/m
	dmi_bulk: float = 0 # bulk DMI mJ/m^2
	dmi_interface: float = 2 # interfacial DMI mJ/m^2
	anistropy_uni: float = 0.5  # 1st order uniaxial anisotropy constant, MJ/m^3. NOTE: This is NOT effective anistropy, which takes into account dipolar energy
	interlayer_exchange: float = 0 # interlayer exchange scaling

	def calc_effective_medium (self, prescaled_mat_params, scaling: float):
		# scale the effective medium, which includes the FM and spacer layers
		mu0 = 4e-7 * math.pi

		# no scaling
		self.landau_damping = prescaled_mat_params.landau_damping
		self.interlayer_exchange = prescaled_mat_params.interlayer_exchange

		# scaling according to Woo, S. et al. Nature Materials 15, 501 (2016).
		self.mag_sat = prescaled_mat_params.mag_sat * scaling
		self.exchange = prescaled_mat_params.exchange * scaling
		self.dmi_bulk = prescaled_mat_params.dmi_bulk * scaling
		self.dmi_interface = prescaled_mat_params.dmi_interface * scaling
		self.anistropy_uni = scaling*(prescaled_mat_params.anistropy_uni - mu0*1e6*prescaled_mat_params.mag_sat**2/2) + mu0*1e6*self.mag_sat**2/2

@dataclass
class GeometryParameter:
	z_fm_single_thickness: int = 1 # thickness in number of cells in z
	z_nm_single_thickness: int = 2 # thickness in number of cells in z
	z_layer_rep_num: int = 1 # number of repetitions
	z_single_rep_thickness: int = 3  # thickness of single repetition in number of cells in z

	z_cell_size: float = 1 # physical size of single cell in z, in nm

	phy_size: Vector = Vector(2048, 2048, 0) # in nm
	grid_cell_count: Vector = Vector(512, 512) # number of cells in simulation, should be power of 2
	pbc: Vector = Vector(0, 0, 0)

	effective_medium_scaling: float = 1 # scaling of material parameters = t_FM/t_repeat

	def calc_auto_parameters(self):
		self.z_single_rep_thickness = self.z_fm_single_thickness + self.z_nm_single_thickness
		self.grid_cell_count.z = self.z_single_rep_thickness * self.z_layer_rep_num - self.z_nm_single_thickness
		self.phy_size.z = self.grid_cell_count.z * self.z_cell_size


@dataclass
class SimulationMetadata:
	commit: str = '' # version control
	stage: int = 0
	loop: int = -1
	sim_name: str = ''
	sim_full_name: str = ''
	walltime: str = '24:00:00'
	sim_id: str = ''
	output_dir: str = ''
	mumax_file: str = ''

	sh_file: str = ''
	production_run: bool = False
	mumax_installed: bool = False
	project_code: string = 'Personal'

	def calc_auto_parameters(self):
		if self.output_dir == '':
			self.output_dir = os.path.join(os.getcwd(), self.sim_name)
		# convert to system specific paths
		self.output_dir = os.path.abspath(self.output_dir)
		self.sim_id = ''.join([random.choice(string.ascii_letters+string.digits) for ch in range(8)])
		self.sim_name_full = self.sim_name + '_st%02d_%02d' % (self.stage, self.loop)+'_'+self.sim_id
		self.mumax_file = os.path.join(self.output_dir, self.sim_name_full + '.mx3')
		self.sh_file = os.path.join(self.output_dir, 'one_sim.sh')
		self.production_run = not os.path.isfile('./not_production_run.txt')  # this will be set automatically by checking if file not_production_run.txt exist in current dir
		status, outputstr = getstatusoutput('mumax3')
		self.mumax_installed = status == 0

@dataclass
class TuningParameters:
	external_Bfield: float = 0

# all experimental parameters
@dataclass
class SimulationParameters:

	# SimulationMetadata
	sim_meta: SimulationMetadata = SimulationMetadata()
	# MaterialParameters
	mat: MaterialParameters = MaterialParameters()
	# MaterialParameters
	mat_scaled: MaterialParameters = MaterialParameters()
	# GeometryParameter
	geom: GeometryParameter = GeometryParameter()
	# TuningParameters
	tune: TuningParameters = TuningParameters()

	def generate_sims(self):
		# this is suppose to generate a parameter space defined by parameter arrays that are assumed to be orthogonal
		result = [outer_product_object_list(self)]
		return flatten(result)


def save_json_file(sim_param: SimulationParameters):
	if not os.path.exists(sim_param.sim_meta.output_dir):
		os.makedirs(sim_param.sim_meta.output_dir)
	json_file = open(os.path.join(sim_param.sim_meta.output_dir, sim_param.sim_meta.sim_name_full +".json"), "w")
	json_str = convert_obj_to_json_recursively(sim_param)
	parsed = json.loads(json_str)
	json.dump(parsed, json_file, sort_keys=True, indent=2)

# Write PBS script for submission to queue
def writing_sh(sim_param: SimulationParameters):
	server_script = textwrap.dedent('''\
	#!/bin/bash
	#PBS -N one_sim
	#PBS -q gpu
	#PBS -l Walltime=%s
	#PBS -l select=1:ncpus=24:mem=24GB
	#PBS -P %s
	module load mumax

	mumax3 %s
	''' % (sim_param.sim_meta.walltime, sim_param.sim_meta.project_code, sim_param.sim_meta.mumax_file)  # 00:00:30
						   )
	# defining the location of the .mx3 script
	sh_file = sim_param.sim_meta.sh_file

	# opening and saving it
	executable_file = open(sh_file, "w")
	executable_file.write(server_script)
	executable_file.close()

	return 0

# qsub the job
def submit_sh(sim_param: SimulationParameters):
	if os.path.isfile(sim_param.sim_meta.sh_file):
		os.system('qsub < %s ' % sim_param.sim_meta.sh_file)

	return 0

def run_n_convert_mumax(sim_param: SimulationParameters):
	if os.path.isfile(sim_param.sim_meta.mumax_file):
		os.system('mumax3 %s ' % sim_param.sim_meta.mumax_file)
		# move output file to current directory
		os.system('mv %s/*.ovf %s' % (os.path.join(sim_param.sim_meta.output_dir, sim_param.sim_meta.sim_name_full + '.out'), sim_param.sim_meta.output_dir))
		# os.system('mumax3-convert -vtk binary %s/*.ovf ' % (sim_param.sim_name_full + '.out'))

# write mumax3 script
def writing_mumax_file(sim_param: SimulationParameters):

	mumax_commands = textwrap.dedent('''\
	Mega :=1e6
	Pico :=1e-12
	Nano :=1e-9
	Mili :=1e-3
	
	// Micromagnetic variables
	Aex_var := %f*Pico  // Exchange in J/m^3
	Msat_var := %f*Mega  //Saturation magnetisation in A/m
	Ku1_var	:= %f*Mega  // Anistropy in J/m^3
	Dbulk_var  := %f*Mili  //Bulk DMI in J/m^2
	Dind_var  := %f*Mili  //Interfacial DMI in J/m^2
	
	// Setting micromagnetic parameters for Region 0
	Aex.SetRegion(0, Aex_var)
	Msat.SetRegion(0, Msat_var)
	Ku1.SetRegion(0, Ku1_var)
	Dbulk.SetRegion(0, Dbulk_var)
	Dind.SetRegion(0, Dind_var)
	
	// Setting micromagnetic parameters for Region 1
	Aex.SetRegion(1, Aex_var)
	Msat.SetRegion(1, Msat_var)
	Ku1.SetRegion(1, Ku1_var)
	Dbulk.SetRegion(1, Dbulk_var)
	Dind.SetRegion(1, Dind_var)
	
	// Micromagnetic parameters for all regions
	alpha  =%f		 // Damping
	AnisU = vector(0, 0, 1) //Uniaxial anisotropy direction 
	B_ext = vector(0, 0, %f) //in Teslas
	
	// Physical size
	size_X	:=%f //sim_param.phy_size.x
	size_Y	:=%f
	size_Z	:=%f
	
	// Total number of simulations cells
	Nx	:=%.0f //sim_param.grid_size.x
	Ny	:=%.0f
	Nz	:=%.0f
	
	// PBC, if any
	PBC_x :=%.0f //sim_param.pbc.x
	PBC_y :=%.0f
	PBC_z :=%.0f

	z_single_rep_thickness := %.0f // thickness of single repetition in number of cells in z
	z_layer_rep_num := %.0f //this many repetitions
	num_of_regions := 2

	//SetPBC(PBC_x, PBC_y, PBC_z)
	SetGridsize(Nx, Ny, Nz)
	SetCellsize(size_X*Nano/Nx, size_Y*Nano/Ny, size_Z*Nano/Nz)

	//geometry
	for layer_number:=0; layer_number<z_layer_rep_num; layer_number++{
		// set adjacent layers to be of different regions
		// so that we could set interlayer exchange coupling 
		// layer 0: FM, layer 1: FM
		defRegion(Mod(layer_number, num_of_regions), layer(layer_number))
	}
	
	// interlayer exchange scaling
	ext_scaleExchange(0, 1, %f)
	
	// full random magnetisation
	m = RandomMagSeed(%d)
	
	TableAdd(B_ext)
	TableAdd(E_Total)
	TableAdd(E_anis)
	TableAdd(E_demag)
	TableAdd(E_exch)
	TableAdd(E_Zeeman)
	tableAdd(ext_topologicalcharge)
	OutputFormat = OVF1_TEXT
	''' % (sim_param.mat_scaled.exchange, sim_param.mat_scaled.mag_sat, sim_param.mat_scaled.anistropy_uni, sim_param.mat_scaled.dmi_bulk, sim_param.mat_scaled.dmi_interface,

		   sim_param.mat_scaled.landau_damping, sim_param.tune.external_Bfield,

		   sim_param.geom.phy_size.x, sim_param.geom.phy_size.y, sim_param.geom.phy_size.z,

		   sim_param.geom.grid_cell_count.x, sim_param.geom.grid_cell_count.y, sim_param.geom.grid_cell_count.z,

		   sim_param.geom.pbc.x, sim_param.geom.pbc.y, sim_param.geom.pbc.z,

		   sim_param.geom.z_single_rep_thickness, sim_param.geom.z_layer_rep_num,

		   sim_param.mat_scaled.interlayer_exchange,

		   rand.randrange(0,2**32)))

	# if production run, relax and save m
	if sim_param.sim_meta.production_run is True:
		mumax_commands = mumax_commands + textwrap.dedent('''\
		tablesave()
		MinimizerStop = 1e-6
		relax()			// high-energy states best minimized by relax()
		saveas(m,"%s")
		tablesave()
		''' % (sim_param.sim_meta.sim_name_full + '_relaxed'))

	# if not production run, just save inital mag
	else:
		mumax_commands = mumax_commands + textwrap.dedent('''\
		saveas(m, "%s")
		'''%(sim_param.sim_meta.sim_name_full + '_init'))

	# defining the location of the .mx3 script
	# executable = os.path.join(sim_param.sim_meta.output_dir, sim_param.sim_meta.sim_name_full + ".mx3")

	# opening and saving it
	mumax_file = open(sim_param.sim_meta.mumax_file, "w")
	mumax_file.write(mumax_commands)
	mumax_file.close()

	return 0

#--------------- main ---------------#

def main():
	# --- CHOOSE INPUT OPTION --- #
	input_dict_list = load_json_file(['../mumax_sim_inputs/input_parameters.json'])

	if not input_dict_list:
		# user chose to cancel
		return

	# --- BIG OUTSIDE LOOP THRU LIST OF INPUT JSON FILES --- #
	for input_dict in input_dict_list:
		sim_params = SimulationParameters()
		update_obj_from_dict_recursively(sim_params, input_dict)

		# generate simulation full name
		sim_params.sim_meta.calc_auto_parameters()

		# save the main input json for record
		save_json_file(sim_params)
		sim_params_list = sim_params.generate_sims()

		for loop, sim_param_i in enumerate(sim_params_list):

			sim_param_i.sim_meta.loop = loop

			# generate new names and calc geometry
			sim_param_i.sim_meta.calc_auto_parameters()
			sim_param_i.geom.calc_auto_parameters()

			# do effective medium scaling
			sim_param_i.mat_scaled.calc_effective_medium(sim_param_i.mat, sim_param_i.geom.effective_medium_scaling)

			# save each individual simulation's json params
			save_json_file(sim_param_i)

			if not os.path.exists(sim_param_i.sim_meta.output_dir):
				os.makedirs(sim_param_i.sim_meta.output_dir)

			sim_param_i.sim_meta.loop = loop
			writing_mumax_file(sim_param_i)
			writing_sh(sim_param_i)

			if sim_param_i.sim_meta.production_run:
				# the real deal, write sh scripts
				submit_sh(sim_param_i)
			else:
				if sim_param_i.sim_meta.mumax_installed:
					run_n_convert_mumax(sim_param_i)

	return

# run the main function
if __name__ == '__main__':
	main()
