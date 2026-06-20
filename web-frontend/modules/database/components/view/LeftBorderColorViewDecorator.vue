<template>
  <div
    class="left-border-color-decorator"
    :style="value ? { 'border-left-color': value } : {}"
    :class="{ 'left-border-color-decorator--active': !!value }"
  ></div>
</template>

<script>
export default {
  name: 'LeftBorderColorViewDecorator',
  props: {
    value: {
      type: String,
      required: false,
      default: null,
    },
  },
}
</script>

<style scoped>
.left-border-color-decorator {
  display: block;
  width: 4px;
  align-self: stretch;
  border-left: 4px solid transparent;
  flex-shrink: 0;
}

.left-border-color-decorator--active {
  border-left-style: solid;
}
</style>
