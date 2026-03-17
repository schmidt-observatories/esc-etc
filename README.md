# STP ETC ESC

This is intended to be the active directory for the public release of the exposure time calculator for the ExtraSolar Camera.

Derived from the exposure time calculator developed by Aaron Goldtooth, with updates from Justin Hom.

Additional Contributions from Sanchit Sabhlok and Jess Johnson.

## Requirements
All important properties related to the instrument including mirrors, optics, coating throughput, filters, and detectors, are stored in the repositories outlined below. 

> [!Note] 
> The exposure time calculator also allows for users to input their own configurations, **but** this feature can only be used if the configuration(s) follow the same organizational structure as defined in these configuration repositories listed. 
> 
> Users can also use the class functions built into the backend to create their own instruments for calculating exposure times.

The installation instructions for these packages can be found on their corresponding GitHub repos. 

### Telescope

1. [config_um](https://github.com/uasal/config_um) - The configuration repo for UA Ultramarine 3m telescope concept.
2. [config_stp](https://github.com/uasal/config_stp) - The configuration repo for the Space Telescope Project 6.5m (https://arxiv.org/abs/2309.04934).

### Instrument
1. [config_stp_esc](https://github.com/uasal/config_stp_esc) - Configuration repo for the ESC instrument.

### UASAL Archive

For full functionality including stellar and galactic spectra, you will need to set up access to the [UASAL archive](https://github.com/uasal/uasal_archive) and add a path variable `$UASAL_ARCHIVE` to your environment, pointing to the location of the cloned UASAL Archive directory. 

The installation instructions for these packages can be found on their corresponding GitHub repos. 

## Dependencies

All UASAL config packages are dependent on [utils_config](https://github.com/uasal/utils_config) but will be automatically installed when installing the configuration repositories.

Additional package dependencies required for the ETC - astropy, numpy, matplotlib, scipy and synphot.

## Installation

The Exposure Time Calculator is a python package that can be installed via a download from GitHub and then installing on your system locally. You can directly clone the [STP ETC ESC GitHub Repo](https://github.com/uasal/stp_etc_esc) or fork the repo and clone the fork. 

```
$ git clone https://github.com/uasal/stp_etc_esc.git
$ cd stp_etc_esc
$ pip install .
```
> [!Note]
> To install package with optional dependencies *(ex. config_stp, config_um, pytest, etc...)*, run the following pip command instead:<br>
> 
> `pip install '.[dev]'`<br>
> **OR**<br>
> `pip install ".[dev]"`
>
> Pytests will be able to be used when installing `stp_etc_esc` with the `.[dev]` command.

The ETC should now be installed on your local machine. To confirm installation, the following import on python should work - 
```
import stp_etc_esc
stp_etc_esc.__version__
```

## Usage

Included in this repository is an [example notebook](https://github.com/uasal/stp_etc_esc/blob/develop/notebooks/ESC_ExposureTimeSNRCalculator_Demo.ipynb) of how to use the exposure time calculator assuming the default configurations. There is also an [executable python script](https://github.com/uasal/stp_etc_esc/blob/develop/notebooks/etc_esc_requirements.py) that will run the exposure time calculator assuming the default configurations and generate figures calculating SNR and noise sources for various individual frame exposure times.



