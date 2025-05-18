import argparse
import numpy as np
import skfuzzy as fuzz
import json

# Input universes
TEMP_RANGE = np.arange(15, 46, 1)
HUM_RANGE = np.arange(20, 101, 1)
LIGHT_RANGE = np.arange(0, 1001, 1)
OUTPUT_RANGE = np.arange(0, 101, 1)

# Temperature MFs
temp_cold = fuzz.trimf(TEMP_RANGE, [15, 15, 25])
temp_medium = fuzz.trimf(TEMP_RANGE, [20, 30, 40])
temp_hot = fuzz.trimf(TEMP_RANGE, [35, 45, 45])

# Humidity MFs
hum_dry = fuzz.trimf(HUM_RANGE, [20, 20, 50])
hum_normal = fuzz.trimf(HUM_RANGE, [40, 60, 80])
hum_wet = fuzz.trimf(HUM_RANGE, [70, 100, 100])

# Light MFs
light_dark = fuzz.trimf(LIGHT_RANGE, [0, 0, 300])
light_normal = fuzz.trimf(LIGHT_RANGE, [200, 500, 800])
light_bright = fuzz.trimf(LIGHT_RANGE, [600, 1000, 1000])

# Fan MFs
fan_off = fuzz.trimf(OUTPUT_RANGE, [0, 0, 25])
fan_low = fuzz.trimf(OUTPUT_RANGE, [10, 30, 50])
fan_medium = fuzz.trimf(OUTPUT_RANGE, [40, 60, 80])
fan_high = fuzz.trimf(OUTPUT_RANGE, [70, 100, 100])

# Mist MFs
mist_off = fuzz.trimf(OUTPUT_RANGE, [0, 0, 25])
mist_low = fuzz.trimf(OUTPUT_RANGE, [10, 30, 50])
mist_medium = fuzz.trimf(OUTPUT_RANGE, [40, 60, 80])
mist_high = fuzz.trimf(OUTPUT_RANGE, [70, 100, 100])

# LED MFs
led_off = fuzz.trimf(OUTPUT_RANGE, [0, 0, 25])
led_dim = fuzz.trimf(OUTPUT_RANGE, [10, 30, 50])
led_normal = fuzz.trimf(OUTPUT_RANGE, [40, 60, 80])
led_bright = fuzz.trimf(OUTPUT_RANGE, [70, 100, 100])

# Rule base
rules = [
    {"IF": {"temp": "hot", "hum": "dry"}, "THEN": {"fan": "high", "mist": "high"}},
    {"IF": {"temp": "hot", "hum": "normal"}, "THEN": {"fan": "high", "mist": "low"}},
    {"IF": {"temp": "hot", "hum": "wet"}, "THEN": {"fan": "medium", "mist": "off"}},

    {"IF": {"temp": "medium", "hum": "dry"}, "THEN": {"fan": "medium", "mist": "medium"}},
    {"IF": {"temp": "medium", "hum": "normal"}, "THEN": {"fan": "medium", "mist": "low"}},
    {"IF": {"temp": "medium", "hum": "wet"}, "THEN": {"fan": "low", "mist": "off"}},

    {"IF": {"temp": "cold", "hum": "dry"}, "THEN": {"fan": "off", "mist": "low"}},
    {"IF": {"temp": "cold", "hum": "normal"}, "THEN": {"fan": "off", "mist": "off"}},
    {"IF": {"temp": "cold", "hum": "wet"}, "THEN": {"fan": "off", "mist": "off"}},

    {"IF": {"light": "dark"}, "THEN": {"led": "bright"}},
    {"IF": {"light": "normal"}, "THEN": {"led": "normal"}},
    {"IF": {"light": "bright"}, "THEN": {"led": "off"}},

    {"IF": {"temp": "hot", "hum": "dry", "light": "dark"}, "THEN": {"fan": "high", "mist": "high", "led": "bright"}},
    {"IF": {"temp": "medium", "hum": "dry", "light": "bright"}, "THEN": {"fan": "medium", "mist": "medium", "led": "off"}},
    {"IF": {"temp": "cold", "light": "dark"}, "THEN": {"fan": "off", "mist": "off", "led": "dim"}}
]

def fuzzy_greenhouse_control(temp, hum, light):
    temp_levels = {
        "cold": fuzz.interp_membership(TEMP_RANGE, temp_cold, temp),
        "medium": fuzz.interp_membership(TEMP_RANGE, temp_medium, temp),
        "hot": fuzz.interp_membership(TEMP_RANGE, temp_hot, temp)
    }

    hum_levels = {
        "dry": fuzz.interp_membership(HUM_RANGE, hum_dry, hum),
        "normal": fuzz.interp_membership(HUM_RANGE, hum_normal, hum),
        "wet": fuzz.interp_membership(HUM_RANGE, hum_wet, hum)
    }

    light_levels = {
        "dark": fuzz.interp_membership(LIGHT_RANGE, light_dark, light),
        "normal": fuzz.interp_membership(LIGHT_RANGE, light_normal, light),
        "bright": fuzz.interp_membership(LIGHT_RANGE, light_bright, light)
    }

    fan_out = {"off": 0, "low": 0, "medium": 0, "high": 0}
    mist_out = {"off": 0, "low": 0, "medium": 0, "high": 0}
    led_out = {"off": 0, "dim": 0, "normal": 0, "bright": 0}

    for rule in rules:
        cond = rule.get("IF", {})
        degrees = []

        if "temp" in cond:
            degrees.append(temp_levels[cond["temp"]])
        if "hum" in cond:
            degrees.append(hum_levels[cond["hum"]])
        if "light" in cond:
            degrees.append(light_levels[cond["light"]])

        if not degrees:
            continue

        activation = min(degrees)

        for out, level in rule["THEN"].items():
            if out == "fan":
                fan_out[level] = max(fan_out[level], activation)
            elif out == "mist":
                mist_out[level] = max(mist_out[level], activation)
            elif out == "led":
                led_out[level] = max(led_out[level], activation)

    fan_agg = np.fmax.reduce([
        fan_out["off"] * fan_off,
        fan_out["low"] * fan_low,
        fan_out["medium"] * fan_medium,
        fan_out["high"] * fan_high
    ])

    mist_agg = np.fmax.reduce([
        mist_out["off"] * mist_off,
        mist_out["low"] * mist_low,
        mist_out["medium"] * mist_medium,
        mist_out["high"] * mist_high
    ])

    led_agg = np.fmax.reduce([
        led_out["off"] * led_off,
        led_out["dim"] * led_dim,
        led_out["normal"] * led_normal,
        led_out["bright"] * led_bright
    ])

    fan_result = fuzz.defuzz(OUTPUT_RANGE, fan_agg, 'centroid')
    mist_result = fuzz.defuzz(OUTPUT_RANGE, mist_agg, 'centroid')
    led_result = fuzz.defuzz(OUTPUT_RANGE, led_agg, 'centroid')

    return {
        "fan": round(fan_result, 2),
        "mist": round(mist_result, 2),
        "led": round(led_result, 2)
    }

# CLI execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fuzzy Greenhouse Controller")
    parser.add_argument("--temp", type=float, required=True, help="Temperature in Celsius")
    parser.add_argument("--hum", type=float, required=True, help="Relative Humidity in %")
    parser.add_argument("--light", type=float, required=True, help="Light intensity in lux")
    parser.add_argument("--json", action="store_true", help="Return result in JSON format")  # <== ✅ เพิ่มตรงนี้
    args = parser.parse_args()

    result = fuzzy_greenhouse_control(args.temp, args.hum, args.light)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Fuzzy Control Output:")
        print("Fan:", result["fan"], "%")
        print("Mist:", result["mist"], "%")
        print("LED:", result["led"], "%")