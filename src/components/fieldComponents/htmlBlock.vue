<template>
  <div>
    <p v-html="content"></p>
  </div>
</template>

<script>
export default {
  name: "HtmlBlock",

  props: {
    label: {
      type: String,
      required: true
    },
    name: {
      type: String,
      required: true
    },
    content: {
      type: String,
      required: true
    }
  }
};
</script>

<style scoped></style>
