<template>
  <div class="dashboard-app dashboard-app--public">
    <div v-if="error" class="public-dashboard__error">
      <p>{{ $t('publicDashboard.notAvailable') }}</p>
    </div>
    <template v-else-if="dashboard">
      <div class="dashboard-app__content">
        <div class="dashboard-app__content-header">
          <div class="dashboard-app__title">{{ dashboard.name }}</div>
          <div
            v-if="dashboard.description"
            class="dashboard-app__description"
          >
            {{ dashboard.description }}
          </div>
        </div>
        <WidgetBoard
          :dashboard="dashboard"
          store-prefix="public/"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useNuxtApp, useAsyncData } from '#app'
import WidgetBoard from '@baserow/modules/dashboard/components/WidgetBoard'
import PublicDashboardService from '@baserow/modules/dashboard/services/publicDashboard'

definePageMeta({
  layout: 'simple',
  middleware: ['settings'],
})

const route = useRoute()
const { $client, $store } = useNuxtApp()

const error = ref(false)
const dashboard = ref(null)

const { data: pageData } = await useAsyncData(
  `public-dashboard-${route.params.slug}`,
  async () => {
    try {
      const slug = route.params.slug
      const { data } = await PublicDashboardService($client).getPublicDashboard(slug)

      await $store.dispatch('public/dashboardApplication/reset')

      data.widgets.forEach((widget) => {
        $store.commit('public/dashboardApplication/ADD_WIDGET', widget)
      })

      // Dispatch each data source and populate store data cache
      await Promise.all(
        data.data_sources.map(async (ds) => {
          $store.commit('public/dashboardApplication/ADD_DATA_SOURCE', ds)
          try {
            const dispatchResult = await PublicDashboardService(
              $client
            ).dispatchPublicDataSource(slug, ds.id)
            $store.commit('public/dashboardApplication/UPDATE_DATA', {
              dataSourceId: ds.id,
              values: dispatchResult.data,
            })
          } catch {
            $store.commit('public/dashboardApplication/UPDATE_DATA', {
              dataSourceId: ds.id,
              values: { _error: true },
            })
          }
        })
      )

      return data
    } catch {
      return null
    }
  }
)

if (pageData.value) {
  dashboard.value = pageData.value
} else {
  error.value = true
}
</script>
