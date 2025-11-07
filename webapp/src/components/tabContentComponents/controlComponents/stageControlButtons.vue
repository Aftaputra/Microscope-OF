<template>
  <div class="uk-flex uk-flex-center uk-flex-middle uk-margin">
    <div class="dpad-grid">
      <button class="uk-button uk-button-primary dpad-btn" @click="move(0, 1, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_upward </span>
      </button>

      <button class="uk-button uk-button-primary dpad-btn" @click="move(-1, 0, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_back </span>
      </button>

      <button class="uk-button uk-button-primary dpad-btn" @click="move(1, 0, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_forward </span>
      </button>

      <button class="uk-button uk-button-primary dpad-btn" @click="move(0, -1, 0)">
        <span class="material-symbols-outlined sync-icon"> arrow_downward </span>
      </button>

      <button class="uk-button uk-button-primary dpad-btn" @click="move(0, 0, -1)">
        <span class="material-symbols-outlined sync-icon"> remove </span>
      </button>

      <button class="uk-button uk-button-primary dpad-btn" @click="move(0, 0, 1)">
        <span class="material-symbols-outlined sync-icon"> add </span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: "StageControlButtons",
  methods: {
    move(x, y, z) {
      this.$root.$emit("globalMoveStepEvent", x, y, z);
    },
  },
};
</script>

<style scoped>
.dpad-grid {
  display: grid;
  grid-template-columns: repeat(3, 40px);
  grid-template-rows: 40px 40px 40px 20px 40px;
  gap: 1px;
  justify-content: center;
  align-items: center;
}

/* Place buttons within grid */
.dpad-grid button:nth-child(1) {
  grid-column: 2;
  grid-row: 1;
}
.dpad-grid button:nth-child(2) {
  grid-column: 1;
  grid-row: 2;
}
.dpad-grid button:nth-child(3) {
  grid-column: 3;
  grid-row: 2;
}
.dpad-grid button:nth-child(4) {
  grid-column: 2;
  grid-row: 3;
}
.dpad-grid button:nth-child(5) {
  grid-column: 1;
  grid-row: 5;
}
.dpad-grid button:nth-child(6) {
  grid-column: 3;
  grid-row: 5;
}

.dpad-btn {
  width: 40px;
  height: 40px;
  justify-content: center;
  align-items: center;
  display: flex;
}
</style>
