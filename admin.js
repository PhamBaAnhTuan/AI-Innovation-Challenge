const loginPanel = document.getElementById('loginPanel');
const loginForm = document.getElementById('loginForm');
const loginButton = document.getElementById('loginButton');
const loginError = document.getElementById('loginError');
const dashboard = document.getElementById('dashboard');
const dashboardMessage = document.getElementById('dashboardMessage');
const registrationsBody = document.getElementById('registrationsBody');
const registrationCount = document.getElementById('registrationCount');
const emptyState = document.getElementById('emptyState');
const logoutButton = document.getElementById('logoutButton');

let csrfToken = '';

function showLogin() {
  csrfToken = '';
  dashboard.classList.add('hidden');
  logoutButton.classList.add('hidden');
  loginPanel.classList.remove('hidden');
}

function showDashboard() {
  loginPanel.classList.add('hidden');
  dashboard.classList.remove('hidden');
  logoutButton.classList.remove('hidden');
}

function setMessage(element, message) {
  element.textContent = message;
  element.classList.toggle('hidden', !message);
}

async function readResponse(response) {
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof result.detail === 'string'
      ? result.detail
      : 'Đã xảy ra lỗi. Vui lòng thử lại.';
    throw new Error(detail);
  }
  return result;
}

function addCell(row, content, className = '') {
  const cell = document.createElement('td');
  if (className) cell.className = className;
  cell.append(content);
  row.append(cell);
  return cell;
}

function addText(parent, tagName, text, className = '') {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function renderRegistrations(registrations) {
  registrationsBody.replaceChildren();
  registrationCount.textContent = `Tổng số: ${registrations.length} đăng ký`;
  emptyState.classList.toggle('hidden', registrations.length > 0);

  registrations.forEach((registration) => {
    const row = document.createElement('tr');
    const teamCell = document.createElement('td');
    addText(
      teamCell,
      'div',
      registration.team_name || 'Cá nhân',
      'team-name'
    );
    addText(
      teamCell,
      'div',
      `${registration.entry_type} thành viên`,
      'muted'
    );
    row.append(teamCell);

    const membersCell = document.createElement('td');
    registration.members_json.forEach((member) => {
      const details = [member.student_id, member.class_name].filter(Boolean).join(' · ');
      addText(membersCell, 'div', member.name || '—');
      if (details) addText(membersCell, 'div', details, 'muted');
    });
    row.append(membersCell);

    const contactCell = document.createElement('td');
    addText(contactCell, 'div', registration.contact_email);
    addText(contactCell, 'div', registration.contact_phone, 'muted');
    row.append(contactCell);

    const productCell = document.createElement('td');
    addText(productCell, 'div', registration.product_name, 'product-name');
    addText(
      productCell,
      'div',
      registration.product_topic === 'learning'
        ? 'AI trong học tập'
        : 'AI phục vụ cộng đồng',
      'muted'
    );
    addText(productCell, 'div', registration.product_format);
    row.append(productCell);

    const createdAt = new Date(registration.created_at);
    addCell(
      row,
      document.createTextNode(
        Number.isNaN(createdAt.getTime())
          ? registration.created_at
          : createdAt.toLocaleString('vi-VN')
      )
    );

    const statusCell = document.createElement('td');
    statusCell.className = 'status-cell';
    const label = document.createElement('label');
    label.className = 'status-label';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = registration.soft_copy_submitted;
    checkbox.setAttribute(
      'aria-label',
      `Đánh dấu đã nộp hồ sơ bản mềm cho ${registration.team_name || registration.product_name}`
    );
    const statusText = document.createElement('span');
    statusText.textContent = checkbox.checked ? 'Đã nộp' : 'Chưa nộp';
    label.append(checkbox, statusText);
    statusCell.append(label);
    row.append(statusCell);

    checkbox.addEventListener('change', async () => {
      const submitted = checkbox.checked;
      checkbox.disabled = true;
      setMessage(dashboardMessage, '');
      try {
        await readResponse(await fetch(
          `/api/admin/registrations/${registration.id}/soft-copy`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': csrfToken
            },
            body: JSON.stringify({ submitted })
          }
        ));
        statusText.textContent = submitted ? 'Đã nộp' : 'Chưa nộp';
      } catch (error) {
        checkbox.checked = !submitted;
        setMessage(dashboardMessage, error.message);
      } finally {
        checkbox.disabled = false;
      }
    });

    registrationsBody.append(row);
  });
}

async function loadRegistrations() {
  const registrations = await readResponse(
    await fetch('/api/admin/registrations', { cache: 'no-store' })
  );
  renderRegistrations(registrations);
  showDashboard();
}

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  loginButton.disabled = true;
  setMessage(loginError, '');

  try {
    const credentials = Object.fromEntries(new FormData(loginForm));
    const result = await readResponse(await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    }));
    csrfToken = result.csrf_token;
    loginForm.reset();
    await loadRegistrations();
  } catch (error) {
    setMessage(loginError, error.message);
  } finally {
    loginButton.disabled = false;
  }
});

logoutButton.addEventListener('click', async () => {
  logoutButton.disabled = true;
  try {
    await readResponse(await fetch('/api/admin/logout', {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrfToken }
    }));
    showLogin();
  } catch (error) {
    setMessage(dashboardMessage, error.message);
  } finally {
    logoutButton.disabled = false;
  }
});

loadRegistrations().catch((error) => {
  showLogin();
  if (error.message !== 'Vui lòng đăng nhập.') {
    setMessage(loginError, error.message);
  }
});
