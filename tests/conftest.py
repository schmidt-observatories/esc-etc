# Headless matplotlib for the whole test session: the ETC's plot paths must
# never try to open a display under pytest/CI.
import matplotlib

matplotlib.use("Agg")
