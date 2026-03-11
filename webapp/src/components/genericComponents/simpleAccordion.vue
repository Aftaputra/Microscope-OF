<template>
  <ul uk-accordion="multiple: true">
    <li>
      <a class="uk-accordion-title" href="#">{{ title }}</a>
      <div class="uk-accordion-content">
        <slot></slot>
      </div>
    </li>
  </ul>
</template>
<script>
export default {
  name: "SimpleAccordion",

  props: {
    title: {
      type: String,
      required: true,
    },
  },
};
</script>
<style scoped></style>
