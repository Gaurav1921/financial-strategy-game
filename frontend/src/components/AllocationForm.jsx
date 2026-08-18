/**
 * This round's Allocate decision: split available cash across Company,
 * Real Estate, Gold, the Market, a Bank deposit, or a loan, plus optional
 * voluntary liquidation and borrowing (GAMEPLAY.md Section 4). Keeps a
 * live "cash remaining" preview so a player can see an over-allocation
 * before the server would reject it.
 */

import { useMemo, useState } from 'react'
import {
  GOLD_LIQUIDATION_HAIRCUT,
  INDUSTRIES,
  REAL_ESTATE_LIQUIDATION_HAIRCUT,
} from '../constants'

const BLANK_FORM = {
  buyCompany: '',
  buyRealEstate: '',
  buyGold: '',
  bankDeposit: '',
  loanDraw: '',
  loanRepay: '',
  liquidateRealEstate: '',
  liquidateGold: '',
  marketIndustry: INDUSTRIES[0],
  marketDirection: 'long',
  marketAmount: '',
}

function num(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
}

function NumberField({ label, hint, value, onChange, max }) {
  return (
    <label className="number-field">
      <span>
        {label}
        {hint && <small>{hint}</small>}
      </span>
      <input
        type="number"
        min="0"
        max={max}
        step="0.1"
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="0"
      />
    </label>
  )
}

export function AllocationForm({ me, onSubmit, submitting }) {
  const [form, setForm] = useState(BLANK_FORM)

  function set(field) {
    return (value) => setForm((prev) => ({ ...prev, [field]: value }))
  }

  const { spent, available, remaining } = useMemo(() => {
    const liquidationCash =
      num(form.liquidateRealEstate) * REAL_ESTATE_LIQUIDATION_HAIRCUT +
      num(form.liquidateGold) * GOLD_LIQUIDATION_HAIRCUT
    const availableCash = me.cash + liquidationCash + num(form.loanDraw)
    const spentCash =
      num(form.buyCompany) +
      num(form.buyRealEstate) +
      num(form.buyGold) +
      num(form.bankDeposit) +
      num(form.loanRepay) +
      num(form.marketAmount)
    return { spent: spentCash, available: availableCash, remaining: availableCash - spentCash }
  }, [form, me.cash])

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit({
      buy_company: num(form.buyCompany),
      buy_real_estate: num(form.buyRealEstate),
      buy_gold: num(form.buyGold),
      bank_deposit: num(form.bankDeposit),
      loan_draw: num(form.loanDraw),
      loan_repay: num(form.loanRepay),
      liquidate_real_estate: num(form.liquidateRealEstate),
      liquidate_gold: num(form.liquidateGold),
      market_industry: num(form.marketAmount) > 0 ? form.marketIndustry : null,
      market_direction: num(form.marketAmount) > 0 ? form.marketDirection : null,
      market_amount: num(form.marketAmount),
    })
  }

  return (
    <form className="allocation-form" onSubmit={handleSubmit}>
      <div className="cash-summary">
        <span>Cash on hand: {me.cash.toFixed(1)}</span>
        <span className={remaining < 0 ? 'error-text' : ''}>
          Remaining after this plan: {remaining.toFixed(1)}
        </span>
      </div>

      <fieldset>
        <legend>Grow</legend>
        <NumberField label="Your Company" value={form.buyCompany} onChange={set('buyCompany')} />
        <NumberField
          label="Real Estate"
          hint="3% buy-in cost"
          value={form.buyRealEstate}
          onChange={set('buyRealEstate')}
        />
        <NumberField label="Gold" value={form.buyGold} onChange={set('buyGold')} />
      </fieldset>

      <fieldset>
        <legend>The Market</legend>
        <label>
          Industry
          <select value={form.marketIndustry} onChange={(event) => set('marketIndustry')(event.target.value)}>
            {INDUSTRIES.map((industry) => (
              <option key={industry} value={industry}>
                {industry}
              </option>
            ))}
          </select>
        </label>
        <label>
          Position
          <select value={form.marketDirection} onChange={(event) => set('marketDirection')(event.target.value)}>
            <option value="long">Long (bet it rises)</option>
            <option value="short">Short (bet it falls)</option>
          </select>
        </label>
        <NumberField label="Amount" value={form.marketAmount} onChange={set('marketAmount')} />
      </fieldset>

      <fieldset>
        <legend>The Bank</legend>
        <NumberField label="Deposit" hint="4%/round, safe" value={form.bankDeposit} onChange={set('bankDeposit')} />
        <NumberField label="Borrow" hint="leverage-priced interest" value={form.loanDraw} onChange={set('loanDraw')} />
        {me.debt > 0 && (
          <NumberField
            label="Repay debt"
            hint={`owe ${me.debt.toFixed(1)}`}
            value={form.loanRepay}
            onChange={set('loanRepay')}
            max={me.debt}
          />
        )}
      </fieldset>

      {(me.real_estate > 0 || me.gold > 0) && (
        <fieldset>
          <legend>Liquidate</legend>
          {me.real_estate > 0 && (
            <NumberField
              label="Sell Real Estate"
              hint={`15% haircut, hold ${me.real_estate.toFixed(1)}`}
              value={form.liquidateRealEstate}
              onChange={set('liquidateRealEstate')}
              max={me.real_estate}
            />
          )}
          {me.gold > 0 && (
            <NumberField
              label="Sell Gold"
              hint={`5% haircut, hold ${me.gold.toFixed(1)}`}
              value={form.liquidateGold}
              onChange={set('liquidateGold')}
              max={me.gold}
            />
          )}
        </fieldset>
      )}

      <div className="allocation-actions">
        <span className="hint-text">Available this round: {available.toFixed(1)} ({spent.toFixed(1)} planned)</span>
        <button type="submit" className="primary" disabled={submitting || remaining < 0}>
          {submitting ? 'Submitted, waiting on others...' : 'Submit'}
        </button>
      </div>
    </form>
  )
}
