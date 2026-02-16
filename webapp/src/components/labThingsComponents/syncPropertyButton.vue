<template>
  <a class="sync-button" @click.prevent="$emit('click')">
    <span
      class="material-symbols-outlined sync-icon"
      title="Reread value from microscope. Required if microscope is updated externally"
    >
      sync
    </span>
  </a>
</template>

<script>
export default {
  name: "SyncPropertyButton",

  emits: ["click"],
};
</script>

<style scoped>
.sync-button {
  flex-grow: 0;
  padding-left: 5px;
  padding-right: 5px;
  vertical-align: middle;
  cursor: pointer;
}

.material-symbols-outlined.sync-icon {
  color: #888;
  transition:
    transform 0.3s ease,
    color 0.3s ease;
}

.material-symbols-outlined.sync-icon:hover {
  transform: rotate(-90deg);
  color: #c5247f;
}
</style>
