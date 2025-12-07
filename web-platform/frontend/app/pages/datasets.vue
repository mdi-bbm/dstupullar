<template>
  <div class="page-container">
    <v-container fluid class="py-6">
      <v-row>
        <v-col cols="12">
          
          <div class="header-container">

            <div class="d-flex align-center">
              <v-icon large color="primary" class="mr-3">mdi-database</v-icon>

              <h1 class="text-h4 font-weight-bold text-primary">
                {{ $t('navigator.datasets') }}
              </h1>
            </div>
            
            <div class="d-flex align-center gap-3">

              <v-btn-toggle v-model="viewMode" density="comfortable" variant="outlined">
                <v-btn value="grid" size="small">
                  <v-icon>mdi-view-grid</v-icon>
                </v-btn>
                <v-btn value="list" size="small">
                  <v-icon>mdi-view-list</v-icon>
                </v-btn>
              </v-btn-toggle>

              <v-btn-toggle v-if="viewMode === 'grid'" v-model="gridSize" density="comfortable" variant="outlined">
                <v-btn :value="2" size="small">
                  <v-icon>mdi-view-grid-outline</v-icon>
                </v-btn>
                <v-btn :value="3" size="small">
                  <v-icon>mdi-view-grid</v-icon>
                </v-btn>
                <v-btn :value="4" size="small">
                  <v-icon>mdi-view-grid-plus</v-icon>
                </v-btn>
              </v-btn-toggle>
              
              <v-select
                v-model="filcomfortable"
                variant="ter"
                :items="filterOptions"
                density="outlined"
                style="width: 200px;"
                hide-details
                prepend-inner-icon="mdi-filter"
                class="filter-control"
              ></v-select>

            </div>

          </div>

          <v-card class="pa-6 dataset-content-card" elevation="2">
            <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
              {{ error }}
            </v-alert>

            <v-row v-if="loading">
              <v-col v-for="n in 6" :key="n" cols="12" sm="6" md="4" lg="4">
                <v-skeleton-loader type="card"></v-skeleton-loader>
              </v-col>
            </v-row>

            <v-row v-else-if="filteredDatasets.length && viewMode === 'grid'">
              <v-col 
                v-for="dataset in filteredDatasets" 
                :key="dataset.dataset_id" 
                cols="12"
                :sm="gridColumns.sm"
                :md="gridColumns.md"
                :lg="gridColumns.lg"
                >
                <DatasetCard 
                  :dataset="dataset" 
                  :view-mode="viewMode"
              
                />
              </v-col>
            </v-row>

            <div v-else-if="filteredDatasets.length && viewMode === 'list'" class="list-container">
              <DatasetCard 
                v-for="dataset in filteredDatasets" 
                :key="dataset.dataset_id" 
                :dataset="dataset"
                :view-mode="viewMode"
        
              />
            </div>

            <div v-else class="text-center py-12 empty-state">
              <v-icon size="64" color="grey-lighten-2" class="mb-4">mdi-database-remove</v-icon>

              <p class="text-h6 text-grey">{{ $t('datasets.notdatasets') }}</p>
              <p class="text-body-1 text-grey mt-2">{{ $t('datasets.create_first') }}</p>

              <v-btn 
                color="primary" 
                class="mt-4"
                :to="'/create_dataset'"
              >
                <v-icon left>mdi-plus</v-icon>
                {{ $t('datasets.create_dataset') }}
              </v-btn>
              
            </div>
          </v-card>

        </v-col>
      </v-row>
    </v-container>

    <MetadataStaticDialog
      v-if="metadataStaticDialog && selectedDataset"
      v-model="metadataStaticDialog"
      :dataset="selectedDataset"
      @saved="handleMetadataSaved"
      @close="metadataStaticDialog = false"
    />

    <UserManagementDialog
      v-if="userManagementDialog && selectedDataset"
      v-model="userManagementDialog"
      :dataset="selectedDataset"
      @close="userManagementDialog = false"
    />
  </div>
</template>

<script setup>
definePageMeta({
  requiresAuth: true 
})

import DatasetCard from '~/components/datasets/DatasetCard.vue'


const { authGet } = useAuthFetch()
const authStore = useAuthStore()
const { t } = useI18n()

const filter = ref('all')
const datasets = ref([])
const loading = ref(false)
const error = ref('')
const selectedDataset = ref(null)
const metadataStaticDialog = ref(false)
const userManagementDialog = ref(false)
const viewMode = ref('grid')
const gridSize = ref(3)
const filterOptions = ref([
  { title: t('datasets.filter_all'), value: 'all' },
  { title: t('datasets.filter_public'), value: 'public' },
  { title: t('datasets.filter_private'), value: 'private' }
])


const fetchDatasets = async () => {
  loading.value = true
  error.value = ''
  
  try {
    const response = await authGet('/api/datasets/')
 
    datasets.value = response.datasets || []
  } catch (err) {
    error.value = t('datasets.load_error')
    console.error('Error fetching datasets:', err)
  } finally {
    loading.value = false
  }
}

const userDatasets = computed(() => {
  return datasets.value
})

const filteredDatasets = computed(() => {
  if (filter.value === 'public') {
    return userDatasets.value.filter(d => d.access_type === 'Public')
  }

  if (filter.value === 'private') {
    return userDatasets.value.filter(d => d.access_type !== 'Public')
  }

  return userDatasets.value
})

const gridColumns = computed(() => {
  const size = gridSize.value
  return {
    sm: 12 / Math.min(size, 2),
    md: 12 / Math.min(size, 3),
    lg: 12 / size
  }
})

const handleMetadataSaved = () => {
  metadataStaticDialog.value = false
}

onMounted(async () => {
  const savedViewMode = localStorage.getItem('datasets-view-mode')
  const savedGridSize = localStorage.getItem('datasets-grid-size')
  
  if (savedViewMode) viewMode.value = savedViewMode
  if (savedGridSize) gridSize.value = parseInt(savedGridSize)

  await fetchDatasets()
})

watch(() => t('datasets.filter_all'), () => {
  filterOptions.value = [
    { title: t('datasets.filter_all'), value: 'all' },
    { title: t('datasets.filter_public'), value: 'public' },
    { title: t('datasets.filter_private'), value: 'private' }
  ]
})

watch([viewMode, gridSize], ([newViewMode, newGridSize]) => {
  localStorage.setItem('datasets-view-mode', newViewMode)
  localStorage.setItem('datasets-grid-size', newGridSize.toString())
})
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background: linear-gradient(135deg, 
    rgba(var(--v-theme-primary), 0.03) 0%, 
    rgba(var(--v-theme-secondary), 0.03) 100%);
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
  padding: 0 16px;
}

.dataset-content-card {
  border-radius: 16px;
  
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  margin: 0 16px;
}

.list-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  border-radius: 12px;
  background: rgba(var(--v-theme-background), 0.5);
}

.filter-control {
  flex-shrink: 0;
  min-width: 200px;
}

/* @media (max-width: 960px) {
  .header-container {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .filter-control {
    margin-left: 0 !important;
    max-width: 100%;
  }
  
  .dataset-content-card {
    padding: 20px !important;
    margin: 0 12px;
  }
}

@media (max-width: 600px) {
  .dataset-content-card {
    padding: 16px !important;
    border-radius: 12px;
    margin: 0 8px;
  }
  
  .header-container {
    margin-bottom: 16px;
    padding: 0 8px;
  }
} */
</style>