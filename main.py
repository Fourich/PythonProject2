from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
calculation_history = []
next_history_id = 1

CALC_TYPE_NAMES = {
    'income': 'Доход',
    'rate': 'Ставка',
    'start_sum': 'Старт',
    'period': 'Срок',
    'payment': 'Пополнения'
}


def to_float(value, default=0):
    try:
        return float(str(value).replace(' ', '').replace(',', '.'))
    except ValueError:
        return default


def get_period_in_years(period, period_unit):
    if period_unit == 'months':
        return period / 12
    return period


def get_periods_per_year(period):
    if period == 'daily':
        return 365
    return 12 / int(period)


def calculate_final_sum(start_sum, monthly_payment, rate, years, reinvest, reinvest_period,
                        add_period, add_index, tax_enabled, tax, inflation_enabled, inflation):
    months = int(years * 12)
    monthly_rate = rate / 100 / 12
    balance = start_sum
    total_payments = start_sum
    pending_percent = 0
    total_tax = 0
    current_add_sum = monthly_payment
    years_data = []
    months_data = []

    if reinvest_period == 'daily':
        capitalization_step = 1
    else:
        capitalization_step = int(reinvest_period)

    add_step = int(add_period)

    for month in range(1, months + 1):
        if month > 1 and (month - 1) % 12 == 0:
            current_add_sum += current_add_sum * add_index / 100

        if current_add_sum and month % add_step == 0:
            balance += current_add_sum
            total_payments += current_add_sum

        month_percent = balance * monthly_rate

        if tax_enabled:
            month_tax = month_percent * tax / 100
            month_percent -= month_tax
            total_tax += month_tax

        if reinvest:
            pending_percent += month_percent
            if month % capitalization_step == 0:
                balance += pending_percent
                pending_percent = 0
        else:
            pending_percent += month_percent

        current_total = balance + pending_percent
        current_profit = current_total - total_payments

        real_month_sum = current_total
        month_inflation_loss = 0
        if inflation_enabled:
            month_inflation_multiplier = (1 + inflation / 100) ** (month / 12)
            real_month_sum = current_total / month_inflation_multiplier
            month_inflation_loss = current_total - real_month_sum

        months_data.append({
            'month': month,
            'year': (month - 1) // 12 + 1,
            'balance': round(current_total, 2),
            'payments': round(total_payments, 2),
            'profit': round(current_profit, 2),
            'real_sum': round(real_month_sum, 2),
            'inflation_loss': round(month_inflation_loss, 2)
        })

        if month % 12 == 0:
            year = month // 12
            nominal_sum = current_total
            real_sum = nominal_sum
            inflation_loss = 0

            if inflation_enabled:
                inflation_multiplier = (1 + inflation / 100) ** year
                real_sum = nominal_sum / inflation_multiplier
                inflation_loss = nominal_sum - real_sum

            years_data.append({
                'year': year,
                'balance': round(nominal_sum, 2),
                'payments': round(total_payments, 2),
                'profit': round(current_profit, 2),
                'real_sum': round(real_sum, 2),
                'inflation_loss': round(inflation_loss, 2)
            })

    final_sum = balance + pending_percent
    real_final_sum = final_sum
    inflation_loss = 0

    if inflation_enabled:
        inflation_multiplier = (1 + inflation / 100) ** years
        real_final_sum = final_sum / inflation_multiplier
        inflation_loss = final_sum - real_final_sum

    return {
        'final_sum': round(final_sum, 2),
        'real_final_sum': round(real_final_sum, 2),
        'total_payments': round(total_payments, 2),
        'profit': round(final_sum - total_payments, 2),
        'total_tax': round(total_tax, 2),
        'inflation_loss': round(inflation_loss, 2),
        'months': months,
        'years_data': years_data,
        'months_data': months_data
    }


def get_final_sum_simple(start_sum, monthly_payment, rate, years, reinvest, reinvest_period, add_period, add_index):
    result = calculate_final_sum(
        start_sum, monthly_payment, rate, years, reinvest, reinvest_period,
        add_period, add_index, False, 0, False, 0
    )
    return result['final_sum']


def find_rate(goal, start_sum, monthly_payment, years, reinvest, reinvest_period, add_period, add_index):
    left = 0
    right = 100

    for _ in range(80):
        middle = (left + right) / 2
        final_sum = get_final_sum_simple(start_sum, monthly_payment, middle, years, reinvest, reinvest_period, add_period, add_index)
        if final_sum < goal:
            left = middle
        else:
            right = middle

    return round((left + right) / 2, 2)


def find_start_sum(goal, monthly_payment, rate, years, reinvest, reinvest_period, add_period, add_index):
    left = 0
    right = goal

    for _ in range(80):
        middle = (left + right) / 2
        final_sum = get_final_sum_simple(middle, monthly_payment, rate, years, reinvest, reinvest_period, add_period, add_index)
        if final_sum < goal:
            left = middle
        else:
            right = middle

    return round((left + right) / 2, 2)


def find_years(goal, start_sum, monthly_payment, rate, reinvest, reinvest_period, add_period, add_index):
    years = 0
    final_sum = start_sum

    while final_sum < goal and years < 100:
        years += 1 / 12
        final_sum = get_final_sum_simple(start_sum, monthly_payment, rate, years, reinvest, reinvest_period, add_period, add_index)

    return round(years, 2)


def find_monthly_payment(goal, start_sum, rate, years, reinvest, reinvest_period, add_period, add_index):
    left = 0
    right = goal

    for _ in range(80):
        middle = (left + right) / 2
        final_sum = get_final_sum_simple(start_sum, middle, rate, years, reinvest, reinvest_period, add_period, add_index)
        if final_sum < goal:
            left = middle
        else:
            right = middle

    return round((left + right) / 2, 2)


@app.route('/clear_history', methods=['POST'])
def clear_history():
    calculation_history.clear()
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    global next_history_id
    values = {
        'calc_type': 'income',
        'goal': 1000000,
        'start_sum': 100000,
        'period': 5,
        'period_unit': 'years',
        'rate': 12,
        'reinvest': True,
        'reinvest_period': '1',
        'monthly_payment': 10000,
        'add_period': '1',
        'add_index': 0,
        'tax_enabled': False,
        'tax': 13,
        'inflation_enabled': False,
        'inflation': 5.91,
        'view_interval': 'years'
    }

    if request.method == 'POST':
        values['calc_type'] = request.form.get('calc_type', 'income')
        values['goal'] = to_float(request.form.get('goal'), 1000000)
        values['start_sum'] = to_float(request.form.get('start_sum'), 100000)
        values['period'] = to_float(request.form.get('period'), 5)
        values['period_unit'] = request.form.get('period_unit', 'years')
        values['rate'] = to_float(request.form.get('rate'), 12)
        values['reinvest'] = request.form.get('reinvest') == '1'
        values['reinvest_period'] = request.form.get('reinvest_period', '1')
        values['monthly_payment'] = to_float(request.form.get('monthly_payment'), 10000)
        values['add_period'] = request.form.get('add_period', '1')
        values['add_index'] = to_float(request.form.get('add_index'), 0)
        values['tax_enabled'] = request.form.get('tax_enabled') == '1'
        values['tax'] = to_float(request.form.get('tax'), 13)
        values['inflation_enabled'] = request.form.get('inflation_enabled') == '1'
        values['inflation'] = to_float(request.form.get('inflation'), 5.91)
        values['view_interval'] = request.form.get('view_interval', 'years')

    years = get_period_in_years(values['period'], values['period_unit'])
    extra_result = None

    if values['calc_type'] == 'rate':
        found_rate = find_rate(values['goal'], values['start_sum'], values['monthly_payment'], years,
                               values['reinvest'], values['reinvest_period'], values['add_period'], values['add_index'])
        values['rate'] = found_rate
        extra_result = f"Нужная ставка: {found_rate}% годовых"

    if values['calc_type'] == 'start_sum':
        found_start_sum = find_start_sum(values['goal'], values['monthly_payment'], values['rate'], years,
                                         values['reinvest'], values['reinvest_period'], values['add_period'], values['add_index'])
        values['start_sum'] = found_start_sum
        extra_result = f"Нужный стартовый капитал: {found_start_sum:,.2f} ₽".replace(',', ' ')

    if values['calc_type'] == 'period':
        found_years = find_years(values['goal'], values['start_sum'], values['monthly_payment'], values['rate'],
                                 values['reinvest'], values['reinvest_period'], values['add_period'], values['add_index'])
        years = found_years
        values['period'] = round(found_years * 12) if values['period_unit'] == 'months' else found_years
        extra_result = f"Срок достижения цели: примерно {found_years} лет"

    if values['calc_type'] == 'payment':
        found_payment = find_monthly_payment(values['goal'], values['start_sum'], values['rate'], years,
                                             values['reinvest'], values['reinvest_period'], values['add_period'], values['add_index'])
        values['monthly_payment'] = found_payment
        extra_result = f"Нужное пополнение: {found_payment:,.2f} ₽".replace(',', ' ')

    result = calculate_final_sum(
        values['start_sum'], values['monthly_payment'], values['rate'], years,
        values['reinvest'], values['reinvest_period'], values['add_period'], values['add_index'],
        values['tax_enabled'], values['tax'], values['inflation_enabled'], values['inflation']
    )

    if request.method == 'POST':
        calculation_history.insert(0, {
            'id': next_history_id,
            'type': values['calc_type'],
            'type_name': CALC_TYPE_NAMES.get(values['calc_type'], values['calc_type']),
            'start_sum': values['start_sum'],
            'monthly_payment': values['monthly_payment'],
            'rate': values['rate'],
            'period': values['period'],
            'period_unit': values['period_unit'],
            'view_interval': values['view_interval'],
            'final_sum': result['final_sum'],
            'profit': result['profit'],
            'years_data': result['years_data'],
            'months_data': result['months_data']
        })
        next_history_id += 1
        del calculation_history[10:]

    return render_template(
        'index.html',
        values=values,
        result=result,
        extra_result=extra_result,
        calculation_history=calculation_history
    )


if __name__ == '__main__':
    app.run(debug=True)
