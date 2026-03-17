// ============================================================
// Tea or Coffee - Google Apps Script Web App
//
// Setup:
//   1. Open your Google Spreadsheet
//   2. Extensions → Apps Script → paste this entire file
//   3. Run setupSheets() once manually (Run → Run function → setupSheets)
//   4. Deploy → New deployment → Web app
//        Execute as: Me
//        Who has access: Anyone
//   5. Copy the deployment URL → set TOC_APPS_SCRIPT_URL in your .env
// ============================================================

const USERS_SHEET = "allowed_users";
const VOTES_SHEET = "user_votes";

// ---- HTTP handlers ----

function doGet(e) {
  try {
    const action = e.parameter.action;
    let data;
    if      (action === "get_user_by_name")     data = getUserByName(e.parameter.name);
    else if (action === "get_user_by_token")    data = getUserByToken(e.parameter.token);
    else if (action === "get_today_totals")     data = getTodayTotals();
    else if (action === "get_user_today_vote")  data = getUserTodayVote(Number(e.parameter.user_id));
    else if (action === "has_user_voted_today") data = hasUserVotedToday(Number(e.parameter.user_id));
    else if (action === "count_today_votes")    data = countTodayVotes();
    else if (action === "get_today_breakdown")  data = getTodayBreakdown();
    else return respond({ error: "Unknown action: " + action });
    return respond({ data: data });
  } catch (err) {
    return respond({ error: err.message });
  }
}

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const action = body.action;
    let data;
    if      (action === "seed_users")              { seedUsers(body.names); data = { success: true }; }
    else if (action === "update_user_token")       { updateUserToken(body.user_id, body.token, body.last_login_at); data = { success: true }; }
    else if (action === "clear_all_tokens")        data = { count: clearAllTokens() };
    else if (action === "insert_vote")             { insertVote(body.user_id, body.tea, body.coffee); data = { success: true }; }
    else if (action === "delete_all_votes")        { deleteAllVotes(); data = { success: true }; }
    else if (action === "delete_user_today_vote")  data = { deleted: deleteUserTodayVote(body.user_id) };
    else return respond({ error: "Unknown action: " + action });
    return respond({ data: data });
  } catch (err) {
    return respond({ error: err.message });
  }
}

function respond(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// ---- Helpers ----

function ss()         { return SpreadsheetApp.getActiveSpreadsheet(); }
function sheet(name)  { return ss().getSheetByName(name); }

function today() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
}

function nowStr() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss");
}

// Safely convert a cell value (may be a Date object) to a string
function toStr(val) {
  if (val instanceof Date) {
    return Utilities.formatDate(val, Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss");
  }
  return String(val);
}

function rowToObj(headers, row) {
  const obj = {};
  headers.forEach(function(h, i) { obj[h] = row[i]; });
  return obj;
}

// ---- One-time setup (run manually from the editor) ----

function setupSheets() {
  const spreadsheet = ss();
  if (!spreadsheet.getSheetByName(USERS_SHEET)) {
    spreadsheet.insertSheet(USERS_SHEET)
      .appendRow(["id", "name", "ip_address", "session_token", "created_at", "last_login_at", "is_active"]);
  }
  if (!spreadsheet.getSheetByName(VOTES_SHEET)) {
    spreadsheet.insertSheet(VOTES_SHEET)
      .appendRow(["id", "user_id", "tea", "coffee", "voted_at"]);
  }
}

// ---- Users ----

function seedUsers(names) {
  setupSheets();
  const s = sheet(USERS_SHEET);
  const data = s.getDataRange().getValues();
  const headers = data[0];
  const nameIdx = headers.indexOf("name");
  const existingNames = new Set(data.slice(1).map(function(r) { return r[nameIdx]; }));
  const ids = data.slice(1).map(function(r) { return Number(r[0]); }).filter(Boolean);
  let nextId = ids.length > 0 ? Math.max.apply(null, ids) + 1 : 1;
  const now = nowStr();
  names.forEach(function(name) {
    if (!existingNames.has(name)) {
      s.appendRow([nextId++, name, "", "", now, "", 1]);
    }
  });
}

function getUserByName(name) {
  const data = sheet(USERS_SHEET).getDataRange().getValues();
  const headers = data[0];
  for (let i = 1; i < data.length; i++) {
    const row = rowToObj(headers, data[i]);
    if (row.name === name) return row;
  }
  return null;
}

function getUserByToken(token) {
  if (!token) return null;
  const data = sheet(USERS_SHEET).getDataRange().getValues();
  const headers = data[0];
  for (let i = 1; i < data.length; i++) {
    const row = rowToObj(headers, data[i]);
    if (row.session_token === token && Number(row.is_active) === 1) return row;
  }
  return null;
}

function updateUserToken(userId, token, lastLoginAt) {
  const s = sheet(USERS_SHEET);
  const data = s.getDataRange().getValues();
  const headers = data[0];
  const tokenCol = headers.indexOf("session_token") + 1;
  const loginCol = headers.indexOf("last_login_at") + 1;
  for (let i = 1; i < data.length; i++) {
    if (Number(data[i][0]) === Number(userId)) {
      s.getRange(i + 1, tokenCol).setValue(token || "");
      if (lastLoginAt) s.getRange(i + 1, loginCol).setValue(lastLoginAt);
      return;
    }
  }
}

function clearAllTokens() {
  const s = sheet(USERS_SHEET);
  const data = s.getDataRange().getValues();
  const headers = data[0];
  const tokenCol = headers.indexOf("session_token") + 1;
  let count = 0;
  for (let i = 1; i < data.length; i++) {
    if (data[i][tokenCol - 1]) {
      s.getRange(i + 1, tokenCol).setValue("");
      count++;
    }
  }
  return count;
}

// ---- Votes ----

function getTodayTotals() {
  const data = sheet(VOTES_SHEET).getDataRange().getValues();
  const headers = data[0];
  const todayStr = today();
  let tea = 0, coffee = 0;
  for (let i = 1; i < data.length; i++) {
    const row = rowToObj(headers, data[i]);
    if (toStr(row.voted_at).substring(0, 10) === todayStr) {
      tea    += Number(row.tea)    || 0;
      coffee += Number(row.coffee) || 0;
    }
  }
  return { tea: tea, coffee: coffee };
}

function getUserTodayVote(userId) {
  const data = sheet(VOTES_SHEET).getDataRange().getValues();
  const headers = data[0];
  const todayStr = today();
  for (let i = 1; i < data.length; i++) {
    const row = rowToObj(headers, data[i]);
    if (Number(row.user_id) === userId && toStr(row.voted_at).substring(0, 10) === todayStr) {
      return { tea: Number(row.tea), coffee: Number(row.coffee) };
    }
  }
  return null;
}

function hasUserVotedToday(userId) {
  return getUserTodayVote(userId) !== null;
}

function countTodayVotes() {
  const data = sheet(VOTES_SHEET).getDataRange().getValues();
  const headers = data[0];
  const todayStr = today();
  let count = 0;
  for (let i = 1; i < data.length; i++) {
    if (toStr(rowToObj(headers, data[i]).voted_at).substring(0, 10) === todayStr) count++;
  }
  return count;
}

function insertVote(userId, tea, coffee) {
  const s = sheet(VOTES_SHEET);
  const data = s.getDataRange().getValues();
  const maxId = data.slice(1).reduce(function(m, r) { return Math.max(m, Number(r[0]) || 0); }, 0);
  s.appendRow([maxId + 1, userId, tea, coffee, nowStr()]);
}

function deleteAllVotes() {
  const s = sheet(VOTES_SHEET);
  const last = s.getLastRow();
  if (last > 1) s.deleteRows(2, last - 1);
}

function deleteUserTodayVote(userId) {
  const s = sheet(VOTES_SHEET);
  const data = s.getDataRange().getValues();
  const headers = data[0];
  const todayStr = today();
  for (let i = 1; i < data.length; i++) {
    const row = rowToObj(headers, data[i]);
    if (Number(row.user_id) === Number(userId) && toStr(row.voted_at).substring(0, 10) === todayStr) {
      s.deleteRow(i + 1);
      return true;
    }
  }
  return false;
}

function getTodayBreakdown() {
  const usersData = sheet(USERS_SHEET).getDataRange().getValues();
  const usersHeaders = usersData[0];
  const users = {};
  for (let i = 1; i < usersData.length; i++) {
    const u = rowToObj(usersHeaders, usersData[i]);
    users[Number(u.id)] = u.name;
  }
  const votesData = sheet(VOTES_SHEET).getDataRange().getValues();
  const votesHeaders = votesData[0];
  const todayStr = today();
  const result = [];
  for (let i = 1; i < votesData.length; i++) {
    const v = rowToObj(votesHeaders, votesData[i]);
    if (toStr(v.voted_at).substring(0, 10) === todayStr) {
      result.push({
        name:   users[Number(v.user_id)] || "Unknown",
        tea:    Number(v.tea)    || 0,
        coffee: Number(v.coffee) || 0,
      });
    }
  }
  result.sort(function(a, b) { return a.name.localeCompare(b.name); });
  return result;
}
