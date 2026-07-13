<!-- Illumination control component — cool white & warm white LED sliders -->
<template>
  <div>
    <ul uk-accordion="multiple: true">
      <li class="uk-open">
        <a class="uk-accordion-title" href="#">Illumination</a>
        <div class="uk-accordion-content">
          <div class="slider-row">
            <label>Cool White</label>
            <input
              v-model.number="brightnessCool"
              type="range"
              min="0"
              max="1"
              step="0.01"
              class="uk-range"
              @change="setCool"
            />
            <span>{{ Math.round(brightnessCool * 100) }}%</span>
          </div>
          <div class="slider-row">
            <label>Warm White</label>
            <input
              v-model.number="brightnessWarm"
              type="range"
              min="0"
              max="1"
              step="0.01"
              class="uk-range"
              @change="setWarm"
            />
            <span>{{ Math.round(brightnessWarm * 100) }}%</span>
          </div>
          <div class="uk-margin-small-top">
            <action-button
              thing="illumination"
              action="set_led"
              :submit-data="{ led_on: true }"
              submit-label="ON"
              :can-terminate="false"
            />
            <action-button
              thing="illumination"
              action="set_led"
              :submit-data="{ led_on: false }"
              submit-label="OFF"
              :can-terminate="false"
            />
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script>
import ActionButton from "../../labThingsComponents/actionButton.vue";

export default {
  name: "IlluminationControl",
  components: { ActionButton },

  data() {
    return {
      brightnessCool: 0,
      brightnessWarm: 0,
    };
  },

  async mounted() {
    this.brightnessCool = await this.readThingProperty("illumination", "brightness_cool") ?? 0;
    this.brightnessWarm = await this.readThingProperty("illumination", "brightness_warm") ?? 0;
  },

methods: {
  async setCool() {
    await this.writeThingProperty("illumination", "brightness_cool", this.brightnessCool);
  },
  async setWarm() {
    await this.writeThingProperty("illumination", "brightness_warm", this.brightnessWarm);
  },
},
};
</script>

<style scoped>
.slider-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.slider-row label {
  width: 75px;
  font-size: 0.85em;
}
.slider-row span {
  width: 35px;
  font-size: 0.85em;
  text-align: right;
}
</style>