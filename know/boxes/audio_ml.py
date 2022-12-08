"""Ingredients for audio ml"""


from slang import fixed_step_chunker, mk_chk_fft
from slang.spectrop import logarithmic_bands_matrix


# The following is just so linting does complain about the imports of the these objects,
# which might lead to their inadvertent deletion.
_ = mk_chk_fft, fixed_step_chunker, logarithmic_bands_matrix


# def mk_spectral_projector()
