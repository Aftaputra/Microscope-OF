<template>
  <!-- Grid managing tab content -->
  <div class="uk-height-1-1 view-component">
    <div class="uk-padding-small">
      <statusPane class="uk-width-large" />
    </div>
    <div class="uk-padding-small">
      <h2>Intended use</h2>
      <p>
        The OpenFlexure system, including hardware, software and peripherals, is intended solely for
        research, educational, training, and non-clinical use.<br />It is not a certified medical
        device, and must not be relied upon for diagnosis, treatment, patient care, or other
        clinical purposes. <br /><br />Any use outside the stated intended purpose is the sole
        responsibility of the user.
      </p>
    </div>
    <div class="uk-padding-small">
      <h2>Links</h2>
      <a
        class="uk-link"
        target="_blank"
        href="https://gitlab.com/openflexure/openflexure-microscope-server/-/issues"
      >
        Report an issue
      </a>
    </div>
  </div>
</template>

<script>
import statusPane from "./aboutComponents/statusPane.vue";

export default {
  name: "AboutContent",

  components: {
    statusPane,
  },
};
</script>
