<template>
  <div class="card-number">
    {{ value }}
  </div>
</template>

<script>
export default {
  name: 'RowCardFieldRunningCount',
  height: 16,
  props: {
    value: {
      type: null,
      default: null,
    },
  },
}
</script>
