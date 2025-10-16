# A list of all the settings in a IMXxx.json:

## version:

I assume this needs to be 2.0

## target

Needs to be bcm2835

## Algorithms

### rpi.black_level

contains one key-value pair. `black_level: 4096`

### rpi.dpc

Defective pixel correction, default off(?)

### rpi.lux

For light sensors, not used. Can be emptied?

### rpi.noise

```
"reference_constant": 0,
"reference_slope": 3.67
```

### rpi.geq

Two elements. offset should be 65535 in all cases we've found. Slope unknown

### rpi.sdn

Spatial denoise. Warning on startup asks us to move it into rpi.denoise, even if empty

### rpi.awb

Auto white balance. Even though we don't use it, camera can't start without it being minimally populated, which is quite a lot

### rpi.alsc

Auto lens shading correction is calibrated by our microscope, and one suggestion is to ship this as a flat table (all 1s) and use that to check if the microscope is calibrated.

`n_iter: 0` (not adaptive)

_If we provide a flat one, then reset and disable flatfield correction will do the same thing. I'm also not sure these are persistent if you run one of them, then `ofm restart`_

### rpi.contrast

`ce_enable` should be 0 (disabled). Gamma curve linear or not is an open question

### rpi.ccm

We only want to ship one temperature. Currently it's 5000K, the temperature of the LED. However, the diffuser might affect this.

Different for HQ and version 2 cameras: currently we take the temperatures either side of 5000K from `/usr/share/libcamera/ipa/rpi/pisp/imx219.json` or `/usr/share/libcamera/ipa/rpi/pisp/imx477.json`

Python code:

```
import numpy as np

temps = {4650:
        np.array([
            2.18174, -0.70887, -0.47287,
            -0.70196, 2.76426, -1.06231,
            -0.25157, -0.71978, 1.97135
        ]),
        5858:
        np.array(
        [
                2.32392, -0.88421, -0.43971,
                -0.63821, 2.58348, -0.94527,
                -0.28541, -0.54112, 1.82653
        ])
    }
target_temp = 5000
temp_low, temp_high = sorted(temps.keys())
alpha = (target_temp - temp_low) / (temp_high - temp_low)

print(alpha)

ccm_interp = (1 - alpha) * temps[temp_low] + alpha * temps[temp_high]
print(np.round(ccm_interp, 6))

temps = {4559: np.array(
                        [
                            2.15423, -0.98143, -0.17279,
                            -0.38131, 2.14763, -0.76632,
                            -0.10069, -0.54383, 1.64452
                        ]),
        5881:np.array(
            [
                2.18464, -0.95493, -0.22971,
                -0.36826, 2.00298, -0.63471,
                -0.15219, -0.38055, 1.53274
            ])
    }
target_temp = 5000
temp_low, temp_high = sorted(temps.keys())
alpha = (target_temp - temp_low) / (temp_high - temp_low)

print(alpha)

ccm_interp = (1 - alpha) * temps[temp_low] + alpha * temps[temp_high]
print(np.round(ccm_interp, 6))
```

This will be superseced by using a MacBeth target.

### rpi.sharpen

Currently empty. Sharpening might be something to add in post processing, but not here I expect.

### rpi.hdr

High dynamic range. Not relevant for us. Currently a short snippet.

### rpi.sync

Syncronising between cameras. Not something we're looking at anytime soon.