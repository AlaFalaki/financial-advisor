<template>
  <UserShell>
    <h2>Forms</h2>
    <div class="grid single">
      <div class="panel">
        <h3>Structured Intake</h3>
        <div class="section">
          <h4>Personal</h4>
          <div class="row">
            <div>
              <label>Province</label>
              <input v-model="form.user.province" />
            </div>
            <div>
              <label>Birth Year</label>
              <input type="number" v-model.number="form.user.birthYear" />
            </div>
            <div>
              <label>Marital Status</label>
              <select v-model="form.user.maritalStatus">
                <option value="">Select status</option>
                <option value="single">Single</option>
                <option value="married">Married</option>
                <option value="common-law">Common-law</option>
                <option value="divorced">Divorced</option>
                <option value="widowed">Widowed</option>
              </select>
            </div>
            <div>
              <label>Retirement Year</label>
              <input type="number" v-model.number="form.user.retirementYear" />
            </div>
          </div>
        </div>

        <div class="section">
          <h4>Income</h4>
          <div class="row">
            <div>
              <label>Employment Income Annual</label>
              <input type="number" v-model.number="form.income.employmentIncomeAnnual" />
            </div>
            <div>
              <label>Pension Annual</label>
              <input type="number" v-model.number="form.income.pensionAnnual" />
            </div>
            <div>
              <label>CPP Start Age</label>
              <input type="number" v-model.number="form.income.cppStartAge" />
            </div>
            <div>
              <label>OAS Start Age</label>
              <input type="number" v-model.number="form.income.oasStartAge" />
            </div>
            <div>
              <label>Other Income Annual</label>
              <input type="number" v-model.number="form.income.otherIncomeAnnual" />
            </div>
          </div>
        </div>

        <div class="section">
          <h4>Spending</h4>
          <div class="row">
            <div>
              <label>Target Net Annual</label>
              <input type="number" v-model.number="form.spending.targetNetAnnual" />
            </div>
            <div>
              <label>Inflation Assumption</label>
              <input type="number" step="0.001" v-model.number="form.spending.inflationAssumption" />
            </div>
          </div>
        </div>

        <div class="section">
          <h4>Accounts</h4>
          <div class="row">
            <div>
              <label>RRSP Balance</label>
              <input type="number" v-model.number="form.accounts.rrsp.balance" />
            </div>
            <div>
              <label>TFSA Balance</label>
              <input type="number" v-model.number="form.accounts.tfsa.balance" />
            </div>
            <div>
              <label>Non-Registered Balance</label>
              <input type="number" v-model.number="form.accounts.nonRegistered.balance" />
            </div>
            <div>
              <label>Non-Registered Adjusted Cost Base</label>
              <input type="number" v-model.number="form.accounts.nonRegistered.adjustedCostBase" />
            </div>
          </div>
        </div>

        <div class="section">
          <h4>Investments</h4>
          <div class="row">
            <div>
              <label>Expected Return</label>
              <input type="number" step="0.001" v-model.number="form.assumptions.expectedReturn" />
            </div>
            <div>
              <label>Return Volatility</label>
              <input type="number" step="0.001" v-model.number="form.assumptions.returnVolatility" />
            </div>
            <div>
              <label>Planning Horizon Years</label>
              <input type="number" v-model.number="form.assumptions.planningHorizonYears" />
            </div>
            <div>
              <label>Investment Risk</label>
              <select v-model="form.assumptions.investmentRisk">
                <option value="">Select risk</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label>Return Override %</label>
              <input type="number" step="1" v-model.number="form.assumptions.investmentReturnOverride" />
            </div>
          </div>
        </div>

        <div class="actions">
          <button @click="saveProfile" :disabled="saving">
            <span v-if="saving">Saving…</span>
            <span v-else>Save</span>
          </button>
        </div>
      </div>
    </div>
  </UserShell>
</template>

<script setup lang="ts">
import UserShell from "~/components/UserShell.vue"

const apiFetch = useApiFetch()
const emptyProfile = () => ({
  user: { province: "", birthYear: null, maritalStatus: "", retirementYear: null },
  income: { employmentIncomeAnnual: null, pensionAnnual: null, cppStartAge: null, oasStartAge: null, otherIncomeAnnual: null },
  spending: { targetNetAnnual: null, inflationAssumption: null },
  accounts: {
    tfsa: { balance: null },
    rrsp: { balance: null },
    nonRegistered: { balance: null, adjustedCostBase: null }
  },
  assumptions: {
    expectedReturn: null,
    returnVolatility: null,
    planningHorizonYears: null,
    investmentRisk: "",
    investmentReturnOverride: null
  },
  documents: []
})

const mergeProfile = (base: any, incoming: any) => ({
  ...base,
  ...incoming,
  user: { ...base.user, ...(incoming?.user || {}) },
  income: { ...base.income, ...(incoming?.income || {}) },
  spending: { ...base.spending, ...(incoming?.spending || {}) },
  accounts: {
    ...base.accounts,
    ...(incoming?.accounts || {}),
    tfsa: { ...base.accounts.tfsa, ...(incoming?.accounts?.tfsa || {}) },
    rrsp: { ...base.accounts.rrsp, ...(incoming?.accounts?.rrsp || {}) },
    nonRegistered: {
      ...base.accounts.nonRegistered,
      ...(incoming?.accounts?.nonRegistered || {})
    }
  },
  assumptions: { ...base.assumptions, ...(incoming?.assumptions || {}) }
})

const form = ref(emptyProfile())

const saving = ref(false)

onMounted(async () => {
  const latest = await apiFetch<any>("/api/users/1/profile/latest")
  if (latest?.profile_json) {
    form.value = mergeProfile(emptyProfile(), latest.profile_json)
  }
})

const saveProfile = async () => {
  saving.value = true
  try {
    await apiFetch("/api/users/1/profile", {
      method: "POST",
      body: { profile_json: form.value }
    })
  } finally {
    saving.value = false
  }
}

</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
.panel {
  background: #fff;
  padding: 16px;
  border-radius: 12px;
}
label {
  font-weight: 600;
  display: block;
  margin-top: 10px;
}
.row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.section {
  padding: 12px;
  border: 1px solid #eee;
  border-radius: 10px;
  margin-bottom: 12px;
  background: #fafafa;
}
h4 {
  margin: 0 0 8px 0;
}
textarea {
  width: 100%;
}
button {
  background: var(--accent);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
}
button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
