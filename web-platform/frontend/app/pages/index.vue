<template>
  <v-container class="d-flex align-center justify-center min-vh-100">
    <v-card class="auth-card" :elevation="12">
      <div class="auth-container">

        <div class="form-section">
          
          <div class="form-toggle">
            <v-btn
              :variant="isLogin ? 'flat' : 'text'"
              color="primary"
              @click="isLogin = true"
              class="toggle-btn"
            >
              {{ $t('login.login') }}
            </v-btn>

            <v-btn
              :variant="!isLogin ? 'flat' : 'text'"
              color="success"
              @click="isLogin = false"
              class="toggle-btn"
            >
              {{ $t('login.register') }}
            </v-btn>
          </div>

          <v-form 
            v-if="isLogin"
            @submit.prevent="userLogin"
            class="form-content"
            >
            <h2 class="text-h4 text-center mb-6">{{ $t('login.login') }}</h2>

            <v-text-field
              v-model="loginData.username"
              :label="$t('login.username')"
              prepend-inner-icon="mdi-account"
              variant="outlined"
              :rules="[requiredRule]"
              class="mb-4"
            />

            <v-text-field
              v-model="loginData.password"
              :label="$t('login.password')"
              prepend-inner-icon="mdi-lock"
              variant="outlined"
              :type="showPassword.login ? 'text' : 'password'"
              :append-inner-icon="showPassword.login ? 'mdi-eye' : 'mdi-eye-off'"
              :rules="[requiredRule]"
              @click:append-inner="showPassword.login = !showPassword.login"
              class="mb-6"
            />

            <v-btn 
              block 
              color="primary" 
              size="large" 
              type="submit"
              :loading="loading"
            >
              {{ $t('login.loginact') }}
            </v-btn>

            <p class="text-center mt-4">
              {{ $t('login.noaccount') }}
              <a href="#" @click.prevent="isLogin = false" class="switch-link">
                {{ $t('login.registeract') }}
              </a>
            </p>
          </v-form>

          <v-form 
            v-else
            @submit.prevent="userRegister"
            class="form-content"
            >
            <h2 class="text-h4 text-center mb-6">{{ $t('login.register') }}</h2>

            <v-text-field
              v-model="registerData.username"
              :label="$t('login.username')"
              prepend-inner-icon="mdi-account"
              variant="outlined"
              :rules="[requiredRule, usernameRule]"
              class="mb-4"
            />

            <v-text-field
              v-model="registerData.password"
              :label="$t('login.password')"
              prepend-inner-icon="mdi-lock"
              variant="outlined"
              :type="showPassword.register ? 'text' : 'password'"
              :append-inner-icon="showPassword.register ? 'mdi-eye' : 'mdi-eye-off'"
              :rules="[requiredRule, passwordRule]"
              @click:append-inner="showPassword.register = !showPassword.register"
              class="mb-4"
            />

            <v-text-field
              v-model="registerData.confirmPassword"
              :label="$t('login.password2')"
              prepend-inner-icon="mdi-lock-check"
              variant="outlined"
              :type="showPassword.register ? 'text' : 'password'"
              :rules="[requiredRule, confirmPasswordRule]"
              class="mb-4"
            />

            <v-alert
              v-if="passwordError"
              type="error"
              variant="tonal"
              class="mb-4"
            >
              {{ $t('login.passwordError') }}
            </v-alert>

            <v-btn 
              block 
              color="success" 
              size="large" 
              type="submit"
              :loading="loading"
            >
              {{ $t('login.registeract') }}
            </v-btn>

            <p class="text-center mt-4">
              {{ $t('login.haveaccount') }}
              <a href="#" @click.prevent="isLogin = true" class="switch-link">
                {{ $t('login.loginact') }}
              </a>
            </p>
          </v-form>
        </div>
        
        <div class="welcome-section">
          <div class="welcome-content">
            <h2 class="text-h3 font-weight-bold mb-4">
              {{ isLogin ? $t('login.comeback') : $t('login.hello') }}
            </h2>
            <p class="text-body-1">
              {{ isLogin ? $t('login.welcomeBackMessage') : $t('login.welcomeNewMessage') }}
            </p>
          </div>
        </div>
        
      </div>
    </v-card>
  </v-container>
</template>

<script setup>
definePageMeta({
  requiresAuth: false 
})

const authStore = useAuthStore()
const { t } = useI18n()
const isLogin = ref(true)
const showPassword = ref({
  login: false,
  register: false
})

const passwordError = ref(false)
const loading = ref(false)
const authError = ref('')
const loginData = ref({ username: '', password: '' })
const registerData = ref({ username: '', password: '', confirmPassword: '' })
const requiredRule = (value) => !!value || t('login.requiredField')
const usernameRule = (value) => value.length >= 3 || t('login.usernameMinLength')
const passwordRule = (value) => value.length >= 6 || t('login.passwordMinLength')
const confirmPasswordRule = (value) => value === registerData.value.password || t('login.passwordsMustMatch')

const userLogin = async () => {
  authError.value = ''
  loading.value = true

  try {
    await authStore.login(loginData.value)
  } catch (error) {
    authError.value = error.data?.message || t('login.authError')
  } finally {
    loading.value = false
  }
}

const userRegister = async () => {
  authError.value = ''
  loading.value = true
  passwordError.value = false

  if (registerData.value.password !== registerData.value.confirmPassword) {
    passwordError.value = true
    loading.value = false
    return
  }

  try {
    await authStore.register(registerData.value)
  } catch (error) {
    authError.value = error.data?.message || t('login.registrationError')
  } finally {
    loading.value = false
  }
}

</script>

<style scoped>
.min-vh-100 {
  min-height: 100vh;
}

.auth-card {
  width: 1000px;
  max-width: 95%;
  height: 600px;
  border-radius: 20px;
  overflow: hidden;
}

.auth-container {
  display: flex;
  height: 100%;
}

.form-section {
  width: 50%;
  padding: 40px;
  display: flex;
  flex-direction: column;
}

.form-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 30px;
  justify-content: center;
}

.toggle-btn {
  min-width: 120px;
}

.form-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.switch-link {
  color: primary;
  text-decoration: none;
  font-weight: 600;
  margin-left: 4px;
}

.switch-link:hover {
  text-decoration: underline;
}

.welcome-section {
  width: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
  overflow: hidden;
}

.welcome-content {
  text-align: center;
  z-index: 2;
  max-width: 400px;
}

/* @media (max-width: 960px) {
  .auth-card {
    height: auto;
    margin: 20px;
  }
  
  .auth-container {
    flex-direction: column;
  }
  
  .form-section,
  .welcome-section {
    width: 100%;
    height: auto;
  }
  
  .welcome-section {
    order: -1;
    height: 200px;
  }
  
  .form-content {
    padding: 20px 0;
  }
} */
</style>
