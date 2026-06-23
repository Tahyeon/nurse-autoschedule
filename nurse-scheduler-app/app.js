(function () {
  "use strict";

  var SUPABASE_URL = "https://fztazsbytcnuazqudqlw.supabase.co";
  var SUPABASE_KEY = "sb_publishable_hfz7w4y0sgYPIebRTfRhRw_5X9nBn0s";
  var supabaseClient = window.supabase ? window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY) : null;
  var ORTOOLS_SOLVER_URL = window.NURSE_SOLVER_URL || localStorage.getItem("nurseSolverUrl") || "";
  var KEY = "nurse-flow-scheduler-v1";
  var DOW = ["\uc77c", "\uc6d4", "\ud654", "\uc218", "\ubaa9", "\uae08", "\ud1a0"];
  var SHIFT_CYCLE = ["D", "E", "N", "OFF"];
  var ROLE_LABEL = { head: "\uc218\uac04\ud638\uc0ac", charge: "\ucc28\uc9c0", mid: "\uc561\ud305", newn: "\uc2e0\uaddc", edu: "\uad50\uc721" };
  var WORK_ROLES = ["charge", "mid", "newn"];
  var MAX_DAILY_REQUESTS = 3;
  var ACTING_VALUE = "ACTING";
  var PASSWORD = "0000";
  var PERSONAL_PASSWORDS = { "김가영": "0804", "함주현": "0627", "조하나": "3567", "김나림": "2368" };
  var APP_VERSION = 4;
  var NIGHT_MIN = 7;
  var NIGHT_MAX = 8;
  var AVOID_PAIRS = [["\uae40\ud0dc\ud604", "\ucd5c\uc11c\uc740"], ["\uae40\ub3c4\ud6c8", "\ucd5c\uc11c\uc740"], ["\uae40\ubbfc\uc11c", "\ucd5c\uc11c\uc740"]];
  var bedEditorAuthorized = false;
  var DEFAULT_CLOUD_URL = "https://script.google.com/macros/s/AKfycbxx7omDvgWylD-44mc6VcLFGxJ1MCd5xl3csUF-SzyQqSXfnr0eJYZQpH8K8rsTZ0Rm/exec";
  var TXT = {
    appTitle: "\uac04\ud638\uc0ac \uadfc\ubb34\ud45c \uc790\ub3d9 \uc0dd\uc131\uae30",
    nurseMode: "\uac04\ud638\uc0ac \uadfc\ubb34 \uc2e0\uccad",
    headMode: "\uc218\uac04\ud638\uc0ac \uad00\ub9ac",
    todayMode: "\ud574\ub2f9\uc694\uc77c \uadfc\ubb34\uc790 \ud655\uc778",
    myScheduleMode: "\ub0b4 \uadfc\ubb34\ud45c \ud655\uc778",
    loginTitle: "\uc774\ub984 \uac80\uc0c9 \ud6c4 \ub85c\uadf8\uc778",
    searchName: "\uc774\ub984 \uac80\uc0c9",
    myScheduleTitle: "\ub0b4 \uadfc\ubb34\ud45c \ud655\uc778",
    myScheduleSearch: "\uc774\ub984 \uac80\uc0c9",
    myScheduleHelp: "\uc774\ub984\uc744 \uc120\ud0dd\ud558\uba74 \uc804\uccb4 \uadfc\ubb34\ud45c \ub300\uc2e0 \ub0b4 \uadfc\ubb34\ub9cc \ub2ec\ub825\uc73c\ub85c \ubcf4\uc5ec\uc90d\ub2c8\ub2e4.",
    noPersonalSchedule: "\uc544\uc9c1 \uc800\uc7a5\ub41c \uadfc\ubb34\ud45c\uac00 \uc5c6\uc2b5\ub2c8\ub2e4. \uc218\uac04\ud638\uc0ac \uad00\ub9ac\uc5d0\uc11c \uadfc\ubb34\ud45c\ub97c \uc791\uc131\ud55c \ub4a4 \ud655\uc778\ud558\uc138\uc694.",
    chooseMySchedule: "\uc774\ub984\uc744 \uac80\uc0c9\ud558\uace0 \uc120\ud0dd\ud558\uc138\uc694.",
    notFinalized: "\uc544\uc9c1 \uc644\uc131\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.",
    todayTitle: "\ud574\ub2f9\uc694\uc77c \uadfc\ubb34\uc790 \ud655\uc778",
    todayDay: "\ub0a0\uc9dc",
    bedAssignTitle: "\ud658\uc790 bed \ubc30\uc815",
    bedAssignHelp: "\ucc28\uc9c0 \uc120\uc0dd\ub2d8\ub9cc \uc218\uc815\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4. bed\ub294 1\ubc88\ubd80\ud130 26\ubc88\uae4c\uc9c0 \uc785\ub825\ud558\uc138\uc694. \uc608: 1, 2, 3, 4",
    chargeAuth: "\ucc28\uc9c0 \uc120\ud0dd",
    bedAssignDay: "\ubc30\uc815\ud560 \ub0a0\uc9dc",
    bedAssignShift: "\ubc30\uc815\ud560 \ub4c0\ud2f0",
    openBedAssign: "\ucc28\uc9c0 \ud655\uc778",
    saveBedAssign: "bed \ubc30\uc815 \uc800\uc7a5",
    saveGallery: "\uac24\ub7ec\ub9ac\uc5d0 \uc800\uc7a5",
    offHelp: "\ub0a0\uc9dc\ub97c \ub204\ub974\uba74 \uc544\ub798\uc5d0 D/E/N/OFF\uac00 \ub098\uc635\ub2c8\ub2e4. \uc6d0\ud558\ub294 \uadfc\ubb34\ub97c \uc120\ud0dd\ud55c \ub4a4 \uc2e0\uccad \ubc84\ud2bc\uc744 \ub204\ub974\uc138\uc694.",
    inspectOff: "\ub0a0\uc9dc\ubcc4 \uadfc\ubb34 \uc2e0\uccad\uc790 \ud655\uc778",
    logout: "\ub85c\uadf8\uc544\uc6c3",
    clearMine: "\ub0b4 \uc2e0\uccad \uc804\uccb4 \uc0ad\uc81c",
    submitOff: "\uadfc\ubb34 \uc2e0\uccad",
    settings: "\uadfc\ubb34\ud45c \uc791\uc131 \uc124\uc815",
    year: "\uc5f0\ub3c4",
    month: "\uc6d4",
    holidays: "\uacf5\ud734\uc77c",
    cloudUrl: "\uacf5\uc720 \uc800\uc7a5\uc18c URL",
    cloudWarn: "\uc870\uc791\uc2dc \uadfc\ubb34\uc2e0\uccad\uc774 \ub418\uc9c0 \uc54a\uc73c\ub2c8 \uac74\ub4e4\uc9c0 \ub9c8\uc2dc\uc624.",
    offQuota: "\uae30\uc900 OFF",
    maxOffTotal: "\uc81c\uacf5\ud574\uc57c \ud560 \uc624\ud504",
    needD: "D \ucd5c\uc18c \uc778\uc6d0",
    needE: "E \ucd5c\uc18c \uc778\uc6d0",
    needN: "N \ud544\uc694 \uc778\uc6d0",
    maxD: "D \ucd5c\ub300 \uc778\uc6d0",
    maxE: "E \ucd5c\ub300 \uc778\uc6d0",
    maxN: "N \ucd5c\ub300 \uc778\uc6d0",
    tries: "\ud6c4\ubcf4 \uc0dd\uc131 \uc218",
    generate: "\uadfc\ubb34\ud45c \uc790\ub3d9 \uc791\uc131",
    validate: "\ub2e4\uc2dc \uac80\uc99d",
    regenerate: "\ub2e4\uc2dc \uc791\uc131",
    excel: "\uc5d1\uc140 \ub2e4\uc6b4\ub85c\ub4dc",
    doc: "\ud55c\uae00\uc6a9 \ubb38\uc11c \ub2e4\uc6b4\ub85c\ub4dc",
    reset: "\ucd08\uae30\ud654",
    nurseManage: "\uac04\ud638\uc0ac \uba85\ub2e8 \uad00\ub9ac",
    chargeList: "\ucc28\uc9c0 \uac04\ud638\uc0ac",
    midList: "\uc561\ud305 \uac04\ud638\uc0ac",
    newList: "\uc2e0\uaddc\uac04\ud638\uc0ac",
    saveNurses: "\uba85\ub2e8 \uc800\uc7a5",
    scheduleOptionsTitle: "\uadfc\ubb34\ud45c \uc810\uc218",
    requestStatus: "\uadfc\ubb34 \uc2e0\uccad \ud604\ud669",
    finalUploadTitle: "\ucd5c\uc885 \uc5d1\uc140\ud30c\uc77c \uc5c5\ub85c\ub4dc",
    finalUploadHelp: "\uc218\uac04\ud638\uc0ac\uac00 \uac80\ud1a0\ud558\uace0 \uc218\uc815\ud55c \ucd5c\uc885 \uadfc\ubb34\ud45c \uc5d1\uc140\ud30c\uc77c\uc744 \uc5c5\ub85c\ub4dc\ud558\uba74 \uac04\ud638\uc0ac\ub4e4\uc758 '\ub0b4 \uadfc\ubb34\ud45c \ud655\uc778' \ud654\uba74\uc774 \uc5f4\ub9bd\ub2c8\ub2e4.",
    finalUploadClear: "\ucd5c\uc885\ubcf8 \ucde8\uc18c",
    previousUploadHelp: "\uc774\uc804\ub2ec \ucd5c\uc885 \uadfc\ubb34\ud45c\ub97c \uc62c\ub9ac\uba74 \uc774\uc804\ub2ec \ub9d0\uc77c N \ud6c4 OFF\uac00 \uc774\ubc88\ub2ec \ucd08\uc77c\uc5d0 \ubc18\uc601\ub429\ub2c8\ub2e4.",
    previousUploadClear: "\uc774\uc804\ub2ec \uadfc\ubb34\ud45c \ucde8\uc18c",
    schedule: "\uadfc\ubb34\ud45c",
    validation: "\uac80\uc99d \uacb0\uacfc",
    noSchedule: "\uc218\uac04\ud638\uc0ac \uad00\ub9ac\uc5d0\uc11c \uadfc\ubb34\ud45c \uc790\ub3d9 \uc791\uc131\uc744 \ub204\ub974\uba74 \uacb0\uacfc\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4.",
    noRequests: "\uc544\uc9c1 \uadfc\ubb34 \uc2e0\uccad\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.",
    ok: "\uac80\uc99d \uc644\ub8cc: \ud070 \ubb38\uc81c \uc5c6\uc74c",
    done: "\uc644\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4.",
    syncing: "\ub3d9\uae30\ud654 \uc911\uc785\ub2c8\ub2e4.",
    synced: "\ub3d9\uae30\ud654\ub418\uc5c8\uc2b5\ub2c8\ub2e4.",
    syncFail: "\uacf5\uc720 \uc800\uc7a5\uc18c \uc5f0\uacb0\uc744 \ud655\uc778\ud558\uc138\uc694."
  };
  var PEOPLE = [
    ["\ud55c\uc120\uc544", "head"],
    ["\uc774\ud61c\ubbf8", "charge"], ["\uae40\uc544\uc601", "charge"], ["\uae40\ud604\ud638", "charge"], ["\uacfd\uc9c4\uc601", "charge"], ["\ubc15\ud574\uc900", "charge"], ["\uc5ec\uc218\uc9c4", "charge"],
    ["\uc11c\ubbfc\uc9c4", "mid"], ["\uc2e0\ubbfc\uc9c0", "mid"], ["\uc804\uc9c0\ud574", "mid"], ["\uc774\uc120\uc601", "mid"], ["\uae40\uc138\uc5f0", "mid"], ["\ub958\ub3c4\uc544", "mid"], ["\uae40\ud558\uacbd", "mid"], ["\uc11c\uc9c0\uc624", "mid"], ["\ubc15\uc11c\ud604", "mid"], ["\ucd5c\uc815\uc6d0", "mid"], ["\ubb38\uc720\ubbfc", "mid"], ["\uae40\ud0dc\ud604", "mid"], ["\ucd5c\uc11c\uc740", "mid"], ["\uc774\ud638\uae38", "mid"],
    ["\uae40\ubbfc\uc11c", "newn"], ["\uae40\uc724\ud76c", "newn"], ["\uae40\ud558\ub298", "newn"], ["\uae40\uac00\ud604", "newn"], ["\uc720\uc9c0\ud61c", "newn"], ["\uae40\uac00\ub78c", "newn"], ["\uc784\uac00\uc744", "newn"], ["\uae40\ub3c4\ud6c8", "newn"], ["\uc784\ud6a8\uc120", "newn"], ["\ucd5c\uc601\uc11c", "newn"], ["\uc870\ud558\ub098", "newn"], ["\ud568\uc8fc\ud604", "newn"], ["\uc7a5\uc608\uc9c4", "newn"], ["\uae40\ub098\ub9bc", "newn"], ["\uae40\ud61c\uc9c4", "newn"], ["\uc774\uac00\uc601", "newn"], ["\uae40\uc0c8\ub86c", "newn"], ["\uad8c\uc2dc\uc740", "newn"], ["\uae40\uc900\uc12d", "newn"], ["\uae40\uc7ac\ud658", "newn"], ["\uae40\uc720\uc815", "newn"], ["\ubc15\ud604\uacbd", "newn"],
    ["\uc774\uc18c\uc601", "edu"]
  ];
  var el = {};
  var state = defaultState();

  function defaultState() {
    var now = new Date();
    return {
      year: now.getFullYear(),
      month: now.getMonth() + 1,
      holidays: [],
      cloudUrl: DEFAULT_CLOUD_URL,
      draftRequests: {},
      baseOff: 10,
      maxOffTotal: 12,
      appVersion: APP_VERSION,
      needs: { D: 8, E: 8, N: 7 },
      maxNeeds: { D: 10, E: 10, N: NIGHT_MAX },
      tries: 160,
      nurses: PEOPLE.map(function (p) { return makeNurse(p[0], p[1]); }),
      requests: [],
      loginId: "",
      myScheduleId: "",
      finalSchedule: {},
      finalizedAt: "",
      previousSchedule: {},
      previousUploadedAt: "",
      bedAssignments: {},
      todayDay: now.getDate(),
      bedEditorOpen: false,
      scheduleOptions: [],
      schedule: {},
      score: null
    };
  }

  document.addEventListener("DOMContentLoaded", init);
  if (document.readyState !== "loading") init();

  function init() {
    if (el.root) return;
    mapEls();
    setTexts();
    fillMonth();
    load();
    bind();
    renderAll();
    loadSupabaseInitialData();
  }

  async function loadSupabaseInitialData() {
    await loadNursesFromSupabase();
    await loadSettingsFromSupabase();
    await loadRequestsFromSupabase();
    await loadScheduleFromSupabase();
  }

  async function loadNursesFromSupabase() {
    if (!supabaseClient) {
      el.nfCloudStatus.textContent = "Supabase 라이브러리를 불러오지 못했습니다.";
      return false;
    }

    var result = await supabaseClient
      .from("nurses")
      .select("id, name, role, is_active, created_at")
      .eq("is_active", true)
      .order("created_at", { ascending: true });

    if (result.error) {
      console.error("Supabase 간호사 명단 불러오기 실패:", result.error);
      el.nfCloudStatus.textContent = "Supabase 간호사 명단 불러오기 실패: " + result.error.message;
      return false;
    }

    if (!result.data || !result.data.length) {
      el.nfCloudStatus.textContent = "Supabase 간호사 명단이 비어 있습니다.";
      return false;
    }

    state.nurses = result.data.map(function (n) {
      return { id: n.id, name: n.name, role: n.role };
    });
    if (!nurse(state.loginId)) state.loginId = "";
    if (!nurse(state.myScheduleId)) state.myScheduleId = "";
    state.requests = state.requests.filter(function (r) { return nurse(r.nurseId); });
    state.schedule = normalizeScheduleForCurrentNurses(state.schedule);
    state.finalSchedule = normalizeScheduleForCurrentNurses(state.finalSchedule || {});
    state.previousSchedule = normalizeScheduleForCurrentNurses(state.previousSchedule || {});
    save();
    renderAll();
    el.nfCloudStatus.textContent = "Supabase 간호사 명단 " + result.data.length + "명을 불러왔습니다.";
    return true;
  }

  function mapEls() {
    [
      "nfRefresh", "nfNurseTab", "nfHeadTab", "nfTodayTab", "nfMyScheduleTab", "nfNurseView", "nfHeadView", "nfTodayView", "nfMyScheduleView", "nfCloudUrl", "nfCloudUrlHead", "nfCloudStatus", "nfNameSearch", "nfNameList", "nfOffPanel",
      "nfLoginName", "nfMyRequests", "nfInspectDay", "nfInspectResult", "nfShiftChoices", "nfDayGrid", "nfOffMessage", "nfLogout", "nfSubmitMine", "nfClearMine", "nfReqYear", "nfReqMonth", "nfYear", "nfMonth", "nfHolidays",
      "nfOffQuota", "nfMaxOffTotal", "nfNeedD", "nfNeedE", "nfNeedN", "nfMaxD", "nfMaxE", "nfMaxN", "nfTries", "nfChargeList", "nfMidList", "nfNewList", "nfSaveNurses", "nfGenerate", "nfExcel", "nfScheduleOptions",
      "nfReset", "nfRequestList", "nfScore", "nfSchedule", "nfDoneOverlay", "nfScheduleCard", "nfMyYear", "nfMyMonth", "nfMyScheduleSearch", "nfMyScheduleNameList", "nfMyScheduleSummary", "nfMyScheduleCalendar", "nfSaveMyScheduleImage", "nfTodayYear", "nfTodayMonth", "nfTodayDay", "nfTodayDate", "nfTodayWorkers", "nfChargeAuthName", "nfBedAssignDay", "nfBedAssignShift", "nfOpenBedAssign", "nfSaveBedAssign", "nfBedAssignPanel", "nfPreviousExcelFile", "nfPreviousUploadStatus", "nfPreviousUploadClear", "nfFinalExcelFile", "nfFinalUploadStatus", "nfFinalUploadClear"
    ].forEach(function (id) { el[id] = document.getElementById(id); });
    el.root = document.getElementById("nurseFlowApp");
  }

  function setTexts() {
    qsa("[data-t]", el.root).forEach(function (node) {
      node.textContent = TXT[node.getAttribute("data-t")] || "";
    });
    el.nfNameSearch.placeholder = "\uc608: \uae40\ubbfc\uc11c";
    el.nfCloudUrl.placeholder = "Google Apps Script URL";
    el.nfCloudUrlHead.placeholder = "Google Apps Script URL";
    el.nfBedAssignShift.innerHTML = '<option value="D">\ub370\uc774</option><option value="E">\uc774\ube0c\ub2dd</option><option value="N">\ub098\uc774\ud2b8</option>';
  }

  function fillMonth() {
    for (var m = 1; m <= 12; m++) {
      var op = document.createElement("option");
      op.value = String(m);
      op.textContent = m + "\uc6d4";
      el.nfMonth.appendChild(op);
      el.nfReqMonth.appendChild(op.cloneNode(true));
      el.nfMyMonth.appendChild(op.cloneNode(true));
      el.nfTodayMonth.appendChild(op.cloneNode(true));
    }
    fillBedAssignDays();
    fillTodayDays();
  }

  function fillBedAssignDays() {
    if (!el.nfBedAssignDay) return;
    var current = el.nfBedAssignDay.value;
    el.nfBedAssignDay.innerHTML = range(daysInMonth()).map(function (d) {
      return '<option value="' + d + '">' + d + '\uc77c (' + dow(d) + ')</option>';
    }).join("");
    el.nfBedAssignDay.value = current && Number(current) <= daysInMonth() ? current : String(koreaTodayParts().day <= daysInMonth() ? koreaTodayParts().day : 1);
  }

  function fillTodayDays() {
    if (!el.nfTodayDay) return;
    var current = el.nfTodayDay.value || state.todayDay;
    el.nfTodayDay.innerHTML = range(daysInMonth()).map(function (d) {
      return '<option value="' + d + '">' + d + '\uc77c (' + dow(d) + ')</option>';
    }).join("");
    state.todayDay = clamp(Number(current), 1, daysInMonth());
    el.nfTodayDay.value = String(state.todayDay);
  }

  function bind() {
    el.nfRefresh.addEventListener("click", refreshCurrentData);
    el.nfNurseTab.addEventListener("click", function () { showMode("nurse"); });
    el.nfTodayTab.addEventListener("click", function () {
      setToKoreaToday();
      renderInputs();
      loadSupabaseInitialData();
      showMode("today");
    });
    el.nfMyScheduleTab.addEventListener("click", function () {
      loadSupabaseInitialData();
      showMode("mine");
    });
    el.nfHeadTab.addEventListener("click", function () {
      if (requirePassword("\uc218\uac04\ud638\uc0ac \uad00\ub9ac \uc554\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.")) {
        loadSupabaseInitialData();
        showMode("head");
      }
    });
    el.nfNameSearch.addEventListener("input", renderNameList);
    el.nfMyScheduleSearch.addEventListener("input", renderMyScheduleNameList);
    el.nfInspectDay.addEventListener("change", renderInspectResult);
    el.nfLogout.addEventListener("click", function () { state.loginId = ""; save(); renderAll(); });
    el.nfSubmitMine.addEventListener("click", submitMyRequests);
    el.nfSaveNurses.addEventListener("click", saveNurseLists);
    el.nfClearMine.addEventListener("click", function () {
      if (!requirePassword("\uadfc\ubb34 \uc2e0\uccad/\ubcc0\uacbd \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.", state.loginId)) return;
      state.requests = state.requests.filter(function (r) { return r.nurseId !== state.loginId; });
      if (state.draftRequests) state.draftRequests[state.loginId] = [];
      save(); saveMyRequestsToSupabase(state.loginId, []); renderAll();
    });
    ["nfReqYear", "nfReqMonth"].forEach(function (id) {
      el[id].addEventListener("change", function () { readRequestMonth(); save(); renderAll(); loadSupabaseInitialData(); });
    });
    ["nfMyYear", "nfMyMonth"].forEach(function (id) {
      el[id].addEventListener("change", function () { readMyScheduleMonth(); save(); renderAll(); loadSupabaseInitialData(); });
    });
    ["nfTodayYear", "nfTodayMonth"].forEach(function (id) {
      el[id].addEventListener("change", function () { readTodayDateInputs(true); save(); renderAll(); loadSupabaseInitialData(); });
    });
    el.nfTodayDay.addEventListener("change", function () { readTodayDateInputs(false); save(); renderTodayWorkers(); });
    ["nfYear", "nfMonth"].forEach(function (id) {
      el[id].addEventListener("change", function () { readInputs(); state.schedule = {}; state.score = null; save(); renderAll(); loadSupabaseInitialData(); });
    });
    ["nfHolidays", "nfOffQuota", "nfMaxOffTotal", "nfNeedD", "nfNeedE", "nfNeedN", "nfMaxD", "nfMaxE", "nfMaxN", "nfTries"].forEach(function (id) {
      el[id].addEventListener("change", function () { readInputs(); save(); renderAll(); saveSettingsToSupabase(); loadRequestsFromSupabase(); loadScheduleFromSupabase(); });
    });
    el.nfGenerate.addEventListener("click", async function () {
      readInputs();
      var originalText = el.nfGenerate.textContent;
      el.nfGenerate.disabled = true;
      el.nfGenerate.textContent = "\uc791\uc131\uc911...";
      await sleep(30);
      var ok = await generateBest();
      validateAndRender();
      await saveSettingsToSupabase();
      if (Object.keys(state.schedule || {}).length) {
        await saveScheduleToSupabase();
        alert(ok ? "\uc644\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4." : "\uadfc\ubb34\ud45c\ub97c \uc800\uc7a5\ud588\uc2b5\ub2c8\ub2e4. \uc870\uac74 \ubbf8\ucda9\uc871 \ubd80\ubd84\uc740 \uc5d1\uc140\uc5d0\uc11c \ube68\uac04\uc0c9\uc73c\ub85c \ud45c\uc2dc\ub429\ub2c8\ub2e4.");
      } else {
        showTransientBanner("필수 조건을 만족하지 못해 Supabase에 저장하지 않았습니다.");
      }
      el.nfGenerate.textContent = originalText;
      el.nfGenerate.disabled = false;
    });
    el.nfExcel.addEventListener("click", exportExcel);
    el.nfPreviousExcelFile.addEventListener("change", handlePreviousExcelUpload);
    el.nfPreviousUploadClear.addEventListener("click", clearPreviousSchedule);
    el.nfFinalExcelFile.addEventListener("change", handleFinalExcelUpload);
    el.nfFinalUploadClear.addEventListener("click", clearFinalSchedule);
    el.nfOpenBedAssign.addEventListener("click", openBedAssignEditor);
    el.nfSaveBedAssign.addEventListener("click", saveBedAssignmentsForToday);
    el.nfSaveMyScheduleImage.addEventListener("click", saveMyScheduleImage);
    el.nfBedAssignDay.addEventListener("change", function () { bedEditorAuthorized = false; renderChargeAuthOptions(); renderBedAssignPanel(); });
    el.nfBedAssignShift.addEventListener("change", function () { bedEditorAuthorized = false; renderChargeAuthOptions(); renderBedAssignPanel(); });
    el.nfReset.addEventListener("click", function () {
      if (!confirm("\uc785\ub825\uac12\uacfc \uadfc\ubb34\ud45c\ub97c \ucd08\uae30\ud654\ud560\uae4c\uc694?")) return;
      localStorage.removeItem(KEY);
      state = defaultState();
      renderAll();
    });
  }

  function showMode(mode) {
    var head = mode === "head";
    var mine = mode === "mine";
    var today = mode === "today";
    el.nfHeadView.classList.toggle("hidden", !head);
    el.nfNurseView.classList.toggle("hidden", head || mine || today);
    el.nfTodayView.classList.toggle("hidden", !today);
    el.nfMyScheduleView.classList.toggle("hidden", !mine);
    el.nfHeadTab.classList.toggle("active", head);
    el.nfNurseTab.classList.toggle("active", !head && !mine && !today);
    el.nfTodayTab.classList.toggle("active", today);
    el.nfMyScheduleTab.classList.toggle("active", mine);
    el.nfScheduleCard.classList.toggle("hidden", !head);
    if (today) {
      if (!hasFinalSchedule()) showTransientBanner(TXT.notFinalized);
      renderTodayWorkers();
    }
    if (mine) {
      if (!hasFinalSchedule()) showTransientBanner(TXT.notFinalized);
      renderMySchedule();
    }
  }

  function requirePassword(text, nurseId) {
    var value = prompt(text || "\ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.");
    var me = nurseId ? nurse(nurseId) : null;
    var expected = me && PERSONAL_PASSWORDS[me.name] ? PERSONAL_PASSWORDS[me.name] : PASSWORD;
    if (value === expected) return true;
    if (value !== null) alert("\ube44\ubc00\ubc88\ud638\uac00 \ub9de\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.");
    return false;
  }

  function load() {
    try {
      var saved = JSON.parse(localStorage.getItem(KEY));
      if (saved && saved.nurses) {
        state = Object.assign(defaultState(), saved);
        state.nurses = mergeFixedNurses(state.nurses);
        state.requests = migrateRequests(state.requests, saved.nurses).filter(function (r) { return nurse(r.nurseId); });
        state.cloudUrl = DEFAULT_CLOUD_URL;
        if (!state.draftRequests) state.draftRequests = {};
        normalizeState();
      }
    } catch (e) {}
  }

  function save() { localStorage.setItem(KEY, JSON.stringify(state)); }

  function cloudPayload() {
    return {
      appVersion: APP_VERSION,
      year: state.year,
      month: state.month,
      holidays: state.holidays,
      baseOff: state.baseOff,
      maxOffTotal: state.maxOffTotal,
      needs: state.needs,
      maxNeeds: state.maxNeeds,
      tries: state.tries,
      nurses: state.nurses,
      requests: state.requests,
      schedule: state.schedule,
      score: state.score,
      updatedAt: new Date().toISOString()
    };
  }

  function applyCloudData(data) {
    if (!data) return;
    if (Number(data.year)) state.year = Number(data.year);
    if (Number(data.month)) state.month = Number(data.month);
    if (Array.isArray(data.holidays)) state.holidays = data.holidays;
    if (typeof data.baseOff === "number") state.baseOff = data.baseOff;
    if (typeof data.maxOffTotal === "number") state.maxOffTotal = data.maxOffTotal;
    if (data.needs) state.needs = data.needs;
    if (data.maxNeeds) state.maxNeeds = data.maxNeeds;
    if (Number(data.tries)) state.tries = Number(data.tries);
    var incomingNurses = Array.isArray(data.nurses) ? data.nurses : state.nurses;
    if (Array.isArray(data.nurses)) state.nurses = mergeFixedNurses(data.nurses);
    if (Array.isArray(data.requests)) state.requests = mergeRequestLists(state.requests, data.requests, incomingNurses);
    if (data.schedule) state.schedule = data.schedule;
    if (typeof data.score === "number") state.score = data.score;
    state.draftRequests = {};
    normalizeState();
    save();
    renderAll();
  }

  function normalizeState() {
    if (!state.needs) state.needs = {};
    if (!state.maxNeeds) state.maxNeeds = {};
    if (!state.appVersion && Number(state.baseOff) === 9) state.baseOff = 10;
    if (!Number(state.maxOffTotal)) state.maxOffTotal = 12;
    if (!state.appVersion && Number(state.needs.D) === 10) state.needs.D = 8;
    if (!state.appVersion && Number(state.needs.E) === 10) state.needs.E = 8;
    if (!Number(state.needs.D)) state.needs.D = 8;
    if (!Number(state.needs.E)) state.needs.E = 8;
    if (!Number(state.needs.N)) state.needs.N = NIGHT_MIN;
    if (!Number(state.maxNeeds.D)) state.maxNeeds.D = 10;
    if (!Number(state.maxNeeds.E)) state.maxNeeds.E = 10;
    if (!Number(state.maxNeeds.N)) state.maxNeeds.N = NIGHT_MAX;
    state.needs.D = clamp(Number(state.needs.D), 7, 50);
    state.needs.E = clamp(Number(state.needs.E), 7, 50);
    state.needs.N = NIGHT_MIN;
    state.maxNeeds.D = Math.max(state.needs.D, clamp(Number(state.maxNeeds.D), 7, 50));
    state.maxNeeds.E = Math.max(state.needs.E, clamp(Number(state.maxNeeds.E), 7, 50));
    state.maxNeeds.N = NIGHT_MAX;
    state.maxOffTotal = Math.max(baseOff(), clamp(Number(state.maxOffTotal), 0, 20));
    if (!Number(state.year)) state.year = new Date().getFullYear();
    if (!Number(state.month)) state.month = new Date().getMonth() + 1;
    state.year = clamp(Number(state.year), 2024, 2100);
    state.month = clamp(Number(state.month), 1, 12);
    state.cloudUrl = DEFAULT_CLOUD_URL;
    state.appVersion = APP_VERSION;
  }

  function cloudRequest(action, payload, callback) {
    if (callback) callback(null, { ok: false });
  }

  function cloudLoad() {
    cloudRequest("load", null, applyCloudData);
  }

  function cloudSave() {
    cloudRequest("save", cloudPayload(), function () {});
  }

  function cloudSaveRequests(nurseId, reqs, callback) {
    var payload = {
      appVersion: APP_VERSION,
      year: state.year,
      month: state.month,
      nurseId: nurseId,
      requests: reqs.map(function (r) { return { day: r.day, shift: r.shift }; })
    };
    cloudRequest("saveRequests", payload, function (data, res) {
      if (res && res.ok && data && Array.isArray(data.requests) && requestsSavedForNurse(data.requests, nurseId, reqs)) {
        data.requests = mergeRequestLists(state.requests.filter(function (r) { return r.nurseId !== nurseId; }), data.requests, state.nurses);
        applyCloudData(data);
        if (callback) callback(true);
      } else {
        legacyMergeSaveRequests(nurseId, reqs, callback);
      }
    });
  }

  function legacyMergeSaveRequests(nurseId, reqs, callback) {
    cloudRequest("load", null, function (data) {
      if (data) applyCloudData(data);
      state.requests = state.requests.filter(function (r) { return r.nurseId !== nurseId; });
      reqs.forEach(function (r) {
        state.requests.push({ id: "r" + Date.now() + Math.random().toString(36).slice(2, 6), nurseId: nurseId, day: r.day, shift: r.shift });
      });
      save();
      cloudSave();
      renderAll();
      if (callback) callback(false);
    });
  }

  function cloudDeleteRequest(requestId) {
    cloudRequest("deleteRequest", { requestId: requestId, year: state.year, month: state.month }, function (data) {
      if (data) applyCloudData(data);
    });
  }

  async function loadRequestsFromSupabase() {
    if (!supabaseClient) return false;

    var result = await supabaseClient
      .from("requests")
      .select("id, nurse_id, day, shift")
      .eq("year", state.year)
      .eq("month", state.month)
      .order("day", { ascending: true });

    if (result.error) {
      console.error("Supabase 근무신청 불러오기 실패:", result.error);
      el.nfCloudStatus.textContent = "Supabase 근무신청 불러오기 실패: " + result.error.message;
      return false;
    }

    state.requests = result.data.map(function (r) {
      return { id: r.id, nurseId: r.nurse_id, day: r.day, shift: r.shift };
    });
    state.draftRequests = {};
    save();
    renderAll();
    el.nfCloudStatus.textContent = "Supabase 근무신청 " + result.data.length + "건을 불러왔습니다.";
    return true;
  }

  async function saveMyRequestsToSupabase(nurseId, reqs) {
    if (!supabaseClient) return false;

    var deleteResult = await supabaseClient
      .from("requests")
      .delete()
      .eq("nurse_id", nurseId)
      .eq("year", state.year)
      .eq("month", state.month);

    if (deleteResult.error) {
      console.error("Supabase 기존 근무신청 삭제 실패:", deleteResult.error);
      el.nfOffMessage.innerHTML = msg("error", "근무신청 저장 실패: " + deleteResult.error.message);
      return false;
    }

    if (reqs.length) {
      var rows = reqs.map(function (r) {
        return { nurse_id: nurseId, year: state.year, month: state.month, day: r.day, shift: r.shift };
      });
      var insertResult = await supabaseClient.from("requests").insert(rows);
      if (insertResult.error) {
        console.error("Supabase 근무신청 저장 실패:", insertResult.error);
        el.nfOffMessage.innerHTML = msg("error", "근무신청 저장 실패: " + insertResult.error.message);
        return false;
      }
    }

    await loadRequestsFromSupabase();
    return true;
  }

  async function deleteRequestFromSupabase(requestId) {
    if (!supabaseClient) return false;
    var result = await supabaseClient.from("requests").delete().eq("id", requestId);
    if (result.error) {
      console.error("Supabase 근무신청 삭제 실패:", result.error);
      alert("근무신청 삭제 실패: " + result.error.message);
      return false;
    }
    await loadRequestsFromSupabase();
    return true;
  }

  async function loadSettingsFromSupabase() {
    if (!supabaseClient) return false;

    var result = await supabaseClient
      .from("settings")
      .select("*")
      .eq("year", state.year)
      .eq("month", state.month)
      .maybeSingle();

    if (result.error) {
      console.error("Supabase 설정 불러오기 실패:", result.error);
      el.nfCloudStatus.textContent = "Supabase 설정 불러오기 실패: " + result.error.message;
      return false;
    }

    if (!result.data) {
      clearFinalStateOnly();
      clearPreviousStateOnly();
      return true;
    }

    state.holidays = Array.isArray(result.data.holidays) ? result.data.holidays : [];
    applySettingsPayload(result.data.needs, result.data.max_needs);
    state.baseOff = Number(result.data.base_off);
    state.maxOffTotal = Number(result.data.max_off_total);
    state.tries = Number(result.data.tries);
    normalizeState();
    save();
    renderInputs();
    return true;
  }

  async function saveSettingsToSupabase() {
    if (!supabaseClient) return false;

    var result = await supabaseClient
      .from("settings")
      .upsert({
        year: state.year,
        month: state.month,
        holidays: state.holidays,
        needs: settingsNeedsPayload(),
        max_needs: state.maxNeeds,
        base_off: state.baseOff,
        max_off_total: state.maxOffTotal,
        tries: state.tries,
        updated_at: new Date().toISOString()
      }, { onConflict: "year,month" });

    if (result.error) {
      console.error("Supabase 설정 저장 실패:", result.error);
      el.nfCloudStatus.textContent = "Supabase 설정 저장 실패: " + result.error.message;
      return false;
    }

    el.nfCloudStatus.textContent = "Supabase 설정이 저장되었습니다.";
    return true;
  }

  function applySettingsPayload(needsPayload, maxNeedsPayload) {
    var needs = needsPayload || {};
    var maxNeeds = maxNeedsPayload || {};
    state.needs = {
      D: Number(needs.D || state.needs.D),
      E: Number(needs.E || state.needs.E),
      N: Number(needs.N || state.needs.N)
    };
    state.maxNeeds = {
      D: Number(maxNeeds.D || state.maxNeeds.D),
      E: Number(maxNeeds.E || state.maxNeeds.E),
      N: Number(maxNeeds.N || state.maxNeeds.N)
    };
    state.finalSchedule = normalizeScheduleForCurrentNurses(needs.__finalSchedule || {});
    state.finalizedAt = needs.__finalizedAt || "";
    state.previousSchedule = normalizeScheduleForCurrentNurses(needs.__previousSchedule || {});
    state.previousUploadedAt = needs.__previousUploadedAt || "";
    state.bedAssignments = needs.__bedAssignments || {};
  }

  function settingsNeedsPayload() {
    var payload = {
      D: Number(state.needs.D) || 0,
      E: Number(state.needs.E) || 0,
      N: Number(state.needs.N) || 0
    };
    if (hasFinalSchedule()) {
      payload.__finalSchedule = state.finalSchedule;
      payload.__finalizedAt = state.finalizedAt || new Date().toISOString();
    }
    if (hasPreviousSchedule()) {
      payload.__previousSchedule = state.previousSchedule;
      payload.__previousUploadedAt = state.previousUploadedAt || new Date().toISOString();
    }
    if (state.bedAssignments && Object.keys(state.bedAssignments).length) {
      payload.__bedAssignments = state.bedAssignments;
    }
    return payload;
  }

  async function loadScheduleFromSupabase() {
    if (!supabaseClient) return false;

    var result = await supabaseClient
      .from("schedules")
      .select("schedule_json, score")
      .eq("year", state.year)
      .eq("month", state.month)
      .maybeSingle();

    if (result.error) {
      console.error("Supabase 근무표 불러오기 실패:", result.error);
      el.nfCloudStatus.textContent = "Supabase 근무표 불러오기 실패: " + result.error.message;
      return false;
    }

    if (result.data) {
      state.schedule = normalizeScheduleForCurrentNurses(result.data.schedule_json || {});
      state.score = typeof result.data.score === "number" ? result.data.score : Number(result.data.score || 0);
    } else {
      state.schedule = {};
      state.score = null;
    }

    save();
    renderSchedule();
    validateAndRender(false);
    return true;
  }

  async function saveScheduleToSupabase() {
    if (!supabaseClient || !Object.keys(state.schedule || {}).length) return false;

    state.schedule = normalizeScheduleForCurrentNurses(state.schedule || {});

    var result = await supabaseClient
      .from("schedules")
      .upsert({
        year: state.year,
        month: state.month,
        schedule_json: state.schedule,
        score: state.score,
        updated_at: new Date().toISOString()
      }, { onConflict: "year,month" });

    if (result.error) {
      console.error("Supabase 근무표 저장 실패:", result.error);
      el.nfCloudStatus.textContent = "Supabase 근무표 저장 실패: " + result.error.message;
      return false;
    }

    el.nfCloudStatus.textContent = "Supabase 근무표가 저장되었습니다.";
    return true;
  }

  function requestsSavedForNurse(list, nurseId, reqs) {
    var mine = list.filter(function (r) { return r.nurseId === nurseId; }).map(function (r) { return r.day + ":" + reqShift(r); }).sort().join("|");
    var next = reqs.map(function (r) { return r.day + ":" + r.shift; }).sort().join("|");
    return mine === next;
  }

  function readInputs() {
    var prevYear = state.year;
    var prevMonth = state.month;
    state.year = clamp(Number(el.nfYear.value), 2024, 2100);
    state.month = clamp(Number(el.nfMonth.value), 1, 12);
    if (state.year !== prevYear || state.month !== prevMonth) { clearFinalStateOnly(); clearPreviousStateOnly(); }
    state.holidays = parseDays(el.nfHolidays.value);
    state.baseOff = clamp(Number(el.nfOffQuota.value), 0, 15);
    state.maxOffTotal = Math.max(state.baseOff, clamp(Number(el.nfMaxOffTotal.value), 0, 20));
    state.needs.D = clamp(Number(el.nfNeedD.value), 7, 50);
    state.needs.E = clamp(Number(el.nfNeedE.value), 7, 50);
    state.needs.N = NIGHT_MIN;
    state.maxNeeds.D = Math.max(state.needs.D, clamp(Number(el.nfMaxD.value), 7, 50));
    state.maxNeeds.E = Math.max(state.needs.E, clamp(Number(el.nfMaxE.value), 7, 50));
    state.maxNeeds.N = NIGHT_MAX;
    state.tries = clamp(Number(el.nfTries.value) || autoTries(), 20, 300);
  }

  function readRequestMonth() {
    var prevYear = state.year;
    var prevMonth = state.month;
    state.year = clamp(Number(el.nfReqYear.value), 2024, 2100);
    state.month = clamp(Number(el.nfReqMonth.value), 1, 12);
    state.schedule = {};
    state.score = null;
    state.draftRequests = {};
    if (state.year !== prevYear || state.month !== prevMonth) { clearFinalStateOnly(); clearPreviousStateOnly(); }
  }

  function readMyScheduleMonth() {
    var prevYear = state.year;
    var prevMonth = state.month;
    state.year = clamp(Number(el.nfMyYear.value), 2024, 2100);
    state.month = clamp(Number(el.nfMyMonth.value), 1, 12);
    if (state.year !== prevYear || state.month !== prevMonth) { clearFinalStateOnly(); clearPreviousStateOnly(); }
  }

  function readTodayDateInputs(monthChanged) {
    var prevYear = state.year;
    var prevMonth = state.month;
    state.year = clamp(Number(el.nfTodayYear.value), 2024, 2100);
    state.month = clamp(Number(el.nfTodayMonth.value), 1, 12);
    if (state.year !== prevYear || state.month !== prevMonth) { clearFinalStateOnly(); clearPreviousStateOnly(); }
    if (monthChanged) fillTodayDays();
    state.todayDay = clamp(Number(el.nfTodayDay.value), 1, daysInMonth());
  }

  async function refreshCurrentData() {
    showTransientBanner("\uc0c8\ub85c\uace0\uce68 \uc911\uc785\ub2c8\ub2e4.");
    await loadSupabaseInitialData();
    renderAll();
    showTransientBanner("\uc0c8\ub85c\uace0\uce68\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
  }

  function renderAll() {
    renderInputs();
    renderNameList();
    renderMyScheduleNameList();
    renderOffPanel();
    renderRequests();
    renderSchedule();
    renderScheduleOptions();
    renderMySchedule();
    renderTodayWorkers();
    renderPreviousUploadStatus();
    renderFinalUploadStatus();
    validateAndRender(false);
    var head = el.nfHeadTab.classList.contains("active");
    el.nfScheduleCard.classList.toggle("hidden", !head);
  }

  function renderInputs() {
    el.nfYear.value = state.year;
    el.nfMonth.value = state.month;
    el.nfReqYear.value = state.year;
    el.nfReqMonth.value = state.month;
    el.nfMyYear.value = state.year;
    el.nfMyMonth.value = state.month;
    el.nfTodayYear.value = state.year;
    el.nfTodayMonth.value = state.month;
    fillTodayDays();
    el.nfHolidays.value = (state.holidays || []).join(", ");
    renderNurseListInputs();
    el.nfCloudUrl.value = "";
    el.nfCloudUrlHead.value = "";
    el.nfOffQuota.value = state.baseOff;
    el.nfMaxOffTotal.value = state.maxOffTotal;
    el.nfNeedD.value = state.needs.D;
    el.nfNeedE.value = state.needs.E;
    el.nfNeedN.value = state.needs.N;
    el.nfMaxD.value = state.maxNeeds.D;
    el.nfMaxE.value = state.maxNeeds.E;
    el.nfMaxN.value = state.maxNeeds.N;
    if (!state.tries) state.tries = autoTries();
    el.nfTries.value = state.tries;
    fillBedAssignDays();
  }

  function renderNurseListInputs() {
    el.nfChargeList.value = state.nurses.filter(function (n) { return n.role === "charge"; }).map(function (n) { return n.name; }).join("\n");
    el.nfMidList.value = state.nurses.filter(function (n) { return n.role === "mid"; }).map(function (n) { return n.name; }).join("\n");
    el.nfNewList.value = state.nurses.filter(function (n) { return n.role === "newn"; }).map(function (n) { return n.name; }).join("\n");
  }

  function parseNameList(value) {
    return uniq(String(value || "").split(/[\n,]+/).map(function (v) { return v.trim(); }).filter(Boolean));
  }

  async function saveNurseLists() {
    if (!requirePassword("\uba85\ub2e8 \uc218\uc815 \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.")) return;
    var fixed = state.nurses.filter(function (n) { return n.role === "head" || n.role === "edu"; });
    var next = fixed.slice();
    parseNameList(el.nfChargeList.value).forEach(function (name) { next.push(makeNurse(name, "charge")); });
    parseNameList(el.nfMidList.value).forEach(function (name) { next.push(makeNurse(name, "mid")); });
    parseNameList(el.nfNewList.value).forEach(function (name) { next.push(makeNurse(name, "newn")); });
    state.nurses = mergeFixedNurses(next);
    state.requests = migrateRequests(state.requests, next).filter(function (r) { return nurse(r.nurseId); });
    state.schedule = {};
    save(); renderAll();
    var ok = await saveNurseListsToSupabase(next);
    if (!ok) return;
    await loadNursesFromSupabase();
    state.requests = state.requests.filter(function (r) { return nurse(r.nurseId); });
    state.schedule = normalizeScheduleForCurrentNurses(state.schedule);
    save(); renderAll(); saveScheduleToSupabase();
    alert("\uba85\ub2e8\uc774 \uc800\uc7a5\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
  }

  async function saveNurseListsToSupabase(nextList) {
    if (!supabaseClient) return false;

    var desired = {};
    nextList.filter(function (n) { return WORK_ROLES.indexOf(n.role) >= 0; }).forEach(function (n) {
      desired[n.role + "|" + n.name] = { name: n.name, role: n.role };
    });

    var currentResult = await supabaseClient
      .from("nurses")
      .select("id, name, role, is_active");

    if (currentResult.error) {
      console.error("Supabase 명단 조회 실패:", currentResult.error);
      alert("Supabase 명단 조회 실패: " + currentResult.error.message);
      return false;
    }

    var current = currentResult.data || [];
    var currentByKey = {};
    current.forEach(function (n) { currentByKey[n.role + "|" + n.name] = n; });

    var updates = [];
    var inserts = [];

    Object.keys(desired).forEach(function (key) {
      var found = currentByKey[key];
      if (found) {
        if (!found.is_active) updates.push({ id: found.id, is_active: true });
      } else {
        inserts.push({ name: desired[key].name, role: desired[key].role, is_active: true });
      }
    });

    current.filter(function (n) { return WORK_ROLES.indexOf(n.role) >= 0; }).forEach(function (n) {
      var key = n.role + "|" + n.name;
      if (!desired[key] && n.is_active) updates.push({ id: n.id, is_active: false });
    });

    for (var i = 0; i < updates.length; i++) {
      var updateResult = await supabaseClient
        .from("nurses")
        .update({ is_active: updates[i].is_active })
        .eq("id", updates[i].id);
      if (updateResult.error) {
        console.error("Supabase 명단 업데이트 실패:", updateResult.error);
        alert("Supabase 명단 업데이트 실패: " + updateResult.error.message);
        return false;
      }
    }

    if (inserts.length) {
      var insertResult = await supabaseClient.from("nurses").insert(inserts);
      if (insertResult.error) {
        console.error("Supabase 명단 추가 실패:", insertResult.error);
        alert("Supabase 명단 추가 실패: " + insertResult.error.message);
        return false;
      }
    }

    return true;
  }

  function makeNurse(name, role) { return { id: role + "_" + name.replace(/\s+/g, ""), name: name, role: role }; }

  function legacyNurseId(n) {
    return n.role + "_" + String(n.name || "").replace(/\s+/g, "");
  }

  function normalizeScheduleForCurrentNurses(schedule) {
    var source = schedule || {};
    var normalized = {};
    state.nurses.forEach(function (n) {
      var arr = source[n.id] || source[legacyNurseId(n)];
      normalized[n.id] = Array.isArray(arr) ? arr.slice(0, daysInMonth()) : [];
    });
    return normalized;
  }

  function mergeFixedNurses(list) {
    var fixed = defaultState().nurses.filter(function (n) { return n.role === "head" || n.role === "edu"; });
    var editable = (list || []).filter(function (n) { return WORK_ROLES.indexOf(n.role) >= 0 && n.name; }).map(function (n) { return makeNurse(n.name, n.role); });
    return fixed.concat(editable);
  }

  function migrateRequests(requests, oldNurses) {
    return (requests || []).map(function (r) {
      if (nurse(r.nurseId)) return r;
      var old = (oldNurses || []).find(function (n) { return n.id === r.nurseId; });
      if (!old && /^p\d+$/.test(String(r.nurseId))) {
        var legacy = PEOPLE[Number(String(r.nurseId).slice(1))];
        if (legacy) old = { name: legacy[0], role: legacy[1] };
      }
      if (!old) return r;
      var next = state.nurses.find(function (n) { return n.name === old.name && n.role === old.role; });
      if (!next) return r;
      return Object.assign({}, r, { nurseId: next.id });
    });
  }

  function mergeRequestLists(current, incoming, incomingNurses) {
    var out = {};
    normalizeRequests(current, state.nurses).forEach(function (r) { out[requestKey(r)] = r; });
    normalizeRequests(incoming, incomingNurses).forEach(function (r) { out[requestKey(r)] = r; });
    return Object.keys(out).map(function (key) { return out[key]; }).filter(function (r) { return nurse(r.nurseId); }).sort(function (a, b) {
      return a.day - b.day || nurseName(a.nurseId).localeCompare(nurseName(b.nurseId), "ko") || reqShift(a).localeCompare(reqShift(b));
    });
  }

  function normalizeRequests(list, oldNurses) {
    return migrateRequests(list || [], oldNurses).map(function (r) {
      return {
        id: r.id || ("r" + Date.now() + Math.random().toString(36).slice(2, 6)),
        nurseId: r.nurseId,
        day: Number(r.day),
        shift: reqShift(r)
      };
    }).filter(function (r) {
      return nurse(r.nurseId) && r.day >= 1 && r.day <= daysInMonth() && ["D", "E", "N", "OFF"].indexOf(r.shift) >= 0;
    });
  }

  function requestKey(r) {
    return r.nurseId + "|" + r.day;
  }

  function nurseName(id) {
    var n = nurse(id);
    return n ? n.name : "";
  }

  function renderNameList() {
    var q = (el.nfNameSearch.value || "").trim();
    var list = nursesForLogin().filter(function (n) { return !q || n.name.indexOf(q) >= 0; });
    el.nfNameList.innerHTML = list.map(function (n) {
      return '<button class="name-btn" type="button" data-login="' + n.id + '"><span>' + esc(n.name) + '</span><span class="badge">' + ROLE_LABEL[n.role] + '</span></button>';
    }).join("");
    qsa("[data-login]", el.nfNameList).forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.loginId = btn.getAttribute("data-login");
        save();
        loadRequestsFromSupabase();
        renderAll();
      });
    });
  }

  function renderMyScheduleNameList() {
    var q = (el.nfMyScheduleSearch.value || "").trim();
    var list = nursesForLogin().filter(function (n) { return !q || n.name.indexOf(q) >= 0; });
    el.nfMyScheduleNameList.innerHTML = list.map(function (n) {
      var active = state.myScheduleId === n.id ? " active" : "";
      return '<button class="name-btn' + active + '" type="button" data-my-schedule="' + n.id + '"><span>' + esc(n.name) + '</span><span class="badge">' + ROLE_LABEL[n.role] + '</span></button>';
    }).join("");
    qsa("[data-my-schedule]", el.nfMyScheduleNameList).forEach(function (btn) {
      btn.addEventListener("click", function () {
        state.myScheduleId = btn.getAttribute("data-my-schedule");
        save();
        renderMyScheduleNameList();
        renderMySchedule();
      });
    });
  }

  function renderMySchedule() {
    if (!el.nfMyScheduleCalendar) return;
    if (!hasFinalSchedule()) {
      el.nfMyScheduleSummary.innerHTML = '<div class="personal-empty">' + TXT.noPersonalSchedule + '</div>';
      el.nfMyScheduleCalendar.innerHTML = "";
      el.nfSaveMyScheduleImage.disabled = true;
      return;
    }

    var me = nurse(state.myScheduleId);
    if (!me) {
      el.nfMyScheduleSummary.innerHTML = '<div class="personal-empty">' + TXT.chooseMySchedule + '</div>';
      el.nfMyScheduleCalendar.innerHTML = "";
      el.nfSaveMyScheduleImage.disabled = true;
      return;
    }
    el.nfSaveMyScheduleImage.disabled = false;

    var finalSchedule = state.finalSchedule || {};
    var arr = finalSchedule[me.id] || [];
    var counts = ["D", "E", "N", "OFF"].map(function (shift) {
      return '<span class="personal-count ' + personalShiftClass(shift) + '"><b>' + personalShiftLabel(shift) + '</b> ' + countNurse(finalSchedule, me.id, shift) + '</span>';
    }).join("");

    el.nfMyScheduleSummary.innerHTML =
      '<div class="personal-title"><div><strong>' + state.year + '\ub144 ' + pad(state.month) + '\uc6d4</strong><span>' + esc(me.name) + ' \uc120\uc0dd\ub2d8</span></div></div>' +
      '<div class="personal-counts">' + counts + '</div>';

    var firstDow = new Date(state.year, state.month - 1, 1).getDay();
    var cells = [];
    for (var i = 0; i < firstDow; i++) cells.push('<div class="personal-day muted-day"></div>');
    range(daysInMonth()).forEach(function (day) {
      var shift = arr[day - 1] || "";
      var requested = hasRequest(me.id, day);
      cells.push(
        '<div class="personal-day ' + dayClass(day) + '">' +
          '<div class="personal-date"><span>' + day + '</span><em>' + dow(day) + '</em></div>' +
          '<div class="personal-shift ' + personalShiftClass(shift) + '">' + personalShiftLabel(shift) + '</div>' +
          (requested ? '<div class="personal-mark">\uc2e0\uccad \ubc18\uc601</div>' : '') +
        '</div>'
      );
    });
    while (cells.length % 7 !== 0) cells.push('<div class="personal-day muted-day"></div>');
    el.nfMyScheduleCalendar.innerHTML =
      '<div class="personal-weekdays">' + DOW.map(function (w) { return '<span>' + w + '</span>'; }).join("") + '</div>' +
      '<div class="personal-calendar">' + cells.join("") + '</div>';
  }

  async function saveMyScheduleImage() {
    var me = nurse(state.myScheduleId);
    if (!me || !hasFinalSchedule()) {
      showTransientBanner(TXT.chooseMySchedule);
      return;
    }
    var canvas = drawMyScheduleCanvas(me);
    canvas.toBlob(async function (blob) {
      if (!blob) return;
      var filename = me.name + "_" + state.year + "_" + pad(state.month) + "_\uadfc\ubb34\ud45c.png";
      var file = new File([blob], filename, { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] }) && navigator.share) {
        try {
          await navigator.share({ files: [file], title: filename });
          return;
        } catch (e) {}
      }
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 800);
      showTransientBanner("PNG \uc774\ubbf8\uc9c0\uac00 \uc800\uc7a5\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
    }, "image/png");
  }

  function drawMyScheduleCanvas(me) {
    var scale = 2;
    var width = 980;
    var cellW = Math.floor((width - 56) / 7);
    var cellH = 112;
    var firstDow = new Date(state.year, state.month - 1, 1).getDay();
    var rows = Math.ceil((firstDow + daysInMonth()) / 7);
    var height = 190 + rows * cellH + 42;
    var canvas = document.createElement("canvas");
    canvas.width = width * scale;
    canvas.height = height * scale;
    var ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = "#111827";
    ctx.font = "900 34px Arial, sans-serif";
    ctx.fillText(state.year + "\ub144 " + pad(state.month) + "\uc6d4 \uadfc\ubb34\ud45c", 28, 52);
    ctx.font = "800 20px Arial, sans-serif";
    ctx.fillStyle = "#667085";
    ctx.fillText(me.name + " \uc120\uc0dd\ub2d8", 30, 86);
    ["D", "E", "N", "OFF"].forEach(function (shift, i) {
      var x = 28 + i * 130;
      roundRect(ctx, x, 112, 112, 36, 8, personalCanvasColor(shift));
      ctx.fillStyle = "#fff";
      ctx.font = "900 17px Arial, sans-serif";
      ctx.fillText(personalShiftLabel(shift) + " " + countNurse(state.finalSchedule, me.id, shift), x + 14, 136);
    });
    ctx.font = "900 16px Arial, sans-serif";
    ctx.fillStyle = "#667085";
    DOW.forEach(function (w, i) { ctx.fillText(w, 48 + i * cellW, 174); });
    var arr = state.finalSchedule[me.id] || [];
    range(daysInMonth()).forEach(function (day) {
      var idx = firstDow + day - 1;
      var col = idx % 7;
      var row = Math.floor(idx / 7);
      var x = 28 + col * cellW;
      var y = 190 + row * cellH;
      ctx.strokeStyle = "#d9e2ed";
      ctx.lineWidth = 2;
      roundRect(ctx, x, y, cellW - 6, cellH - 8, 9, "#ffffff", true);
      ctx.fillStyle = "#172033";
      ctx.font = "900 20px Arial, sans-serif";
      ctx.fillText(String(day), x + 12, y + 28);
      var shift = arr[day - 1] || "";
      roundRect(ctx, x + 10, y + 42, cellW - 26, 46, 8, personalCanvasColor(shift));
      ctx.fillStyle = shift ? "#ffffff" : "#98a2b3";
      ctx.font = "900 22px Arial, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(personalShiftLabel(shift), x + (cellW - 6) / 2, y + 72);
      ctx.textAlign = "left";
    });
    return canvas;
  }

  function personalCanvasColor(shift) {
    return ({ D: "#8aa2df", E: "#bd72e4", N: "#34d3ad", OFF: "#e69a6c", MD: "#6ebf8a" })[shift] || "#eef2f7";
  }

  function roundRect(ctx, x, y, w, h, r, fill, stroke) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) ctx.stroke();
  }

  function renderTodayWorkers() {
    if (!el.nfTodayWorkers) return;
    var target = selectedTodayParts();
    el.nfTodayDate.textContent = target.year + "\ub144 " + pad(target.month) + "\uc6d4 " + target.day + "\uc77c (" + DOW[target.weekday] + ")";

    if (!hasFinalSchedule()) {
      el.nfTodayWorkers.innerHTML = '<div class="personal-empty">' + TXT.notFinalized + '</div>';
      return;
    }

    var schedule = state.finalSchedule || {};
    var groups = ["D", "E", "N"].map(function (shift) {
      var names = scheduleNurses().filter(function (n) {
        return (schedule[n.id] || [])[target.day - 1] === shift;
      });
      return todayWorkerGroup(shift, names, target);
    }).join("");
    el.nfTodayWorkers.innerHTML = groups + monthlyActingSummaryHtml();
    renderBedAssignPanel();
  }

  function monthlyActingSummaryHtml() {
    var counts = monthlyActingCounts();
    var items = scheduleNurses().filter(function (n) { return counts[n.id] > 0; }).sort(function (a, b) {
      return counts[b.id] - counts[a.id] || a.name.localeCompare(b.name, "ko");
    });
    return '<div class="acting-summary"><h3>' + state.year + '\ub144 ' + state.month + '\uc6d4 acting \ud69f\uc218</h3><div class="acting-summary-list">' +
      (items.length ? items.map(function (n) { return '<span class="acting-chip">' + esc(n.name) + ' <b>' + counts[n.id] + '\ud68c</b></span>'; }).join("") : '<span class="muted">acting \uae30\ub85d \uc5c6\uc74c</span>') +
      '</div></div>';
  }

  function monthlyActingCounts() {
    var counts = {};
    scheduleNurses().forEach(function (n) { counts[n.id] = 0; });
    Object.keys(state.bedAssignments || {}).forEach(function (dateKey) {
      var parts = dateKey.split("-").map(Number);
      if (parts[0] !== state.year || parts[1] !== state.month) return;
      ["D", "E"].forEach(function (shift) {
        var shiftMap = (((state.bedAssignments || {})[dateKey] || {})[shift] || {});
        Object.keys(shiftMap).forEach(function (id) {
          if (shiftMap[id] === ACTING_VALUE) counts[id] = (counts[id] || 0) + 1;
        });
      });
    });
    return counts;
  }

  function todayWorkerGroup(shift, nurses, today) {
    return '<div class="today-card ' + personalShiftClass(shift) + '">' +
      '<div class="today-card-head"><strong>' + personalShiftLabel(shift) + '</strong><span>' + nurses.length + '\uba85</span></div>' +
      '<div class="today-name-list">' + (nurses.length ? nurses.map(function (n) {
        var beds = bedsForNurse(todayKey(today), shift, n.id);
        var label = isActingAssignment(todayKey(today), shift, n.id) ? 'acting' : (beds.length ? 'bed ' + beds.join(', ') : 'bed \ubbf8\uc9c0\uc815');
        return '<div class="today-name"><div><b>' + esc(n.name) + '</b><span>' + ROLE_LABEL[n.role] + '</span></div><em>' + label + '</em></div>';
      }).join("") : '<div class="today-empty">\ubc30\uc815 \uc5c6\uc74c</div>') + '</div>' +
    '</div>';
  }

  function openBedAssignEditor() {
    var chargeId = el.nfChargeAuthName.value;
    var charge = nurse(chargeId);
    var allowed = previousDutyChargeNurses();
    if (!charge || allowed.every(function (n) { return n.id !== charge.id; })) {
      showTransientBanner("\uc9c1\uc804 \ub4c0\ud2f0 \ucc28\uc9c0\ub9cc bed\ub97c \ubc30\uc815\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.");
      return;
    }
    if (!requirePassword("\ucc28\uc9c0 \ud655\uc778 \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.", charge.id)) return;
    bedEditorAuthorized = true;
    renderBedAssignPanel();
  }

  function renderBedAssignPanel() {
    if (!el.nfBedAssignPanel) return;
    renderChargeAuthOptions();
    el.nfSaveBedAssign.classList.toggle("hidden", !bedEditorAuthorized);
    el.nfBedAssignPanel.classList.toggle("hidden", !bedEditorAuthorized);
    if (!bedEditorAuthorized) {
      el.nfBedAssignPanel.innerHTML = "";
      return;
    }
    var target = bedAssignDateParts();
    if (!hasFinalSchedule()) {
      el.nfBedAssignPanel.innerHTML = '<div class="personal-empty">' + TXT.notFinalized + '</div>';
      return;
    }
    var shift = el.nfBedAssignShift.value || "D";
    var schedule = state.finalSchedule || {};
    var nurses = scheduleNurses().filter(function (n) { return (schedule[n.id] || [])[target.day - 1] === shift; });
    el.nfBedAssignPanel.innerHTML = nurses.length ? nurses.map(function (n) {
      var acting = isActingAssignment(todayKey(target), shift, n.id);
      return '<div class="bed-row"><div><b>' + esc(n.name) + '</b><span>' + ROLE_LABEL[n.role] + '</span></div><div class="bed-input-wrap"><input class="' + (acting ? 'acting-input' : '') + '" data-bed-nurse="' + n.id + '" data-acting="' + (acting ? 'true' : 'false') + '" inputmode="decimal" pattern="[0-9,\\s.-]*" placeholder="1, 2, 3, 4" value="' + (acting ? 'acting' : bedsForNurse(todayKey(target), shift, n.id).join(', ')) + '"><button class="acting-btn' + (acting ? ' active' : '') + '" type="button" data-acting-for="' + n.id + '">acting</button></div></div>';
    }).join("") : '<div class="personal-empty">\uc774 \ub4c0\ud2f0\uc5d0 \ubc30\uc815\ub41c \uac04\ud638\uc0ac\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.</div>';
    qsa("[data-acting-for]", el.nfBedAssignPanel).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var input = el.nfBedAssignPanel.querySelector('[data-bed-nurse="' + btn.getAttribute("data-acting-for") + '"]');
        var active = input.getAttribute("data-acting") === "true";
        input.setAttribute("data-acting", active ? "false" : "true");
        input.value = active ? "" : "acting";
        input.classList.toggle("acting-input", !active);
        btn.classList.toggle("active", !active);
      });
    });
  }

  function renderChargeAuthOptions() {
    if (!el.nfChargeAuthName) return;
    var current = el.nfChargeAuthName.value;
    var charges = previousDutyChargeNurses();
    var prev = previousDutyForAssignment();
    var emptyLabel = prev ? "\uc9c1\uc804 \ub4c0\ud2f0 \ucc28\uc9c0 \uc120\ud0dd" : "\uc9c1\uc804 \ub4c0\ud2f0 \uc5c6\uc74c";
    if (!charges.length && prev) emptyLabel = prev.day + "\uc77c " + personalShiftLabel(prev.shift) + " \ucc28\uc9c0 \uc5c6\uc74c";
    el.nfChargeAuthName.innerHTML = '<option value="">' + emptyLabel + '</option>' + charges.map(function (n) {
      return '<option value="' + n.id + '">' + esc(n.name) + '</option>';
    }).join("");
    if (charges.some(function (n) { return n.id === current; })) el.nfChargeAuthName.value = current;
  }

  function previousDutyForAssignment() {
    var target = bedAssignDateParts();
    var shift = el.nfBedAssignShift.value || "D";
    if (shift === "D") {
      if (target.day <= 1) return null;
      return { day: target.day - 1, shift: "N" };
    }
    if (shift === "E") return { day: target.day, shift: "D" };
    if (shift === "N") return { day: target.day, shift: "E" };
    return null;
  }

  function previousDutyChargeNurses() {
    if (!hasFinalSchedule()) return [];
    var prev = previousDutyForAssignment();
    if (!prev) return [];
    var schedule = state.finalSchedule || {};
    return state.nurses.filter(function (n) {
      return n.role === "charge" && (schedule[n.id] || [])[prev.day - 1] === prev.shift;
    });
  }

  async function saveBedAssignmentsForToday() {
    if (!bedEditorAuthorized) return;
    var target = bedAssignDateParts();
    var key = todayKey(target);
    var shift = el.nfBedAssignShift.value || "D";
    var next = {};
    var used = {};
    var duplicate = "";
    qsa("[data-bed-nurse]", el.nfBedAssignPanel).forEach(function (input) {
      if (input.getAttribute("data-acting") === "true" || String(input.value || "").trim().toLowerCase() === "acting") {
        next[input.getAttribute("data-bed-nurse")] = ACTING_VALUE;
        return;
      }
      var beds = parseBeds(input.value);
      beds.forEach(function (bed) {
        if (used[bed]) duplicate = String(bed);
        used[bed] = true;
      });
      next[input.getAttribute("data-bed-nurse")] = beds;
    });
    if (duplicate) {
      showTransientBanner("bed " + duplicate + "\ubc88\uc774 \uac19\uc740 \ub4c0\ud2f0\uc5d0 \uc911\ubcf5\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
      return;
    }
    if (!state.bedAssignments) state.bedAssignments = {};
    if (!state.bedAssignments[key]) state.bedAssignments[key] = { D: {}, E: {}, N: {} };
    state.bedAssignments[key][shift] = next;
    save();
    renderTodayWorkers();
    await saveSettingsToSupabase();
    showTransientBanner("bed \ubc30\uc815\uc774 \uc800\uc7a5\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
  }

  function renderOffPanel() {
    var me = nurse(state.loginId);
    el.nfOffPanel.classList.toggle("hidden", !me);
    if (!me) return;
    el.nfLoginName.textContent = me.name + " \uc120\uc0dd\ub2d8 OFF \uc2e0\uccad";
    renderMine(me.id);
    renderInspectDays();
    el.nfDayGrid.innerHTML = range(daysInMonth()).map(function (d) {
      var selected = requestForDay(me.id, d);
      var full = !selected && requestCountExcluding(me.id, d) >= MAX_DAILY_REQUESTS;
      return '<button type="button" class="day-chip ' + (selected ? "sel req-" + selected.shift + " " : "") + (full ? "full " : "") + dayClass(d) + '" data-day="' + d + '">' + d + '<br><span class="dow">' + dow(d) + '</span></button>';
    }).join("");
    qsa("[data-day]", el.nfDayGrid).forEach(function (btn) {
      btn.addEventListener("click", function () { toggleDraftRequest(me.id, Number(btn.getAttribute("data-day"))); });
    });
  }

  function renderInspectDays() {
    var current = el.nfInspectDay.value || state.inspectDay || 1;
    el.nfInspectDay.innerHTML = range(daysInMonth()).map(function (d) { return '<option value="' + d + '">' + d + '\uc77c (' + dow(d) + ')</option>'; }).join("");
    el.nfInspectDay.value = current;
    renderInspectResult();
  }

  function renderInspectResult() {
    var day = Number(el.nfInspectDay.value || state.inspectDay || 1);
    var parts = ["D", "E", "N", "OFF"].map(function (shift) {
      var names = state.requests.filter(function (r) { return r.day === day && reqShift(r) === shift; }).map(function (r) { var n = nurse(r.nurseId); return n ? n.name + '(' + ROLE_LABEL[n.role] + ')' : ''; }).filter(Boolean);
      return shift + ' : ' + (names.length ? names.join(', ') : '\uc5c6\uc74c');
    });
    el.nfInspectResult.textContent = day + '\uc77c \uc2e0\uccad - ' + parts.join(' / ');
  }

  function renderMine(nurseId) {
    var reqs = state.requests.filter(function (r) { return r.nurseId === nurseId; }).sort(function (a, b) { return a.day - b.day; });
    el.nfMyRequests.textContent = reqs.length ? "\ub0b4\uac00 \uc2e0\uccad\ud55c \uadfc\ubb34: " + reqs.map(function (r) { return r.day + "\uc77c " + reqShift(r); }).join(", ") : "\ub0b4\uac00 \uc2e0\uccad\ud55c \uadfc\ubb34: \uc5c6\uc74c";
  }

  function selectedRequests(nurseId) {
    if (!state.draftRequests) state.draftRequests = {};
    if (!state.draftRequests[nurseId]) {
      state.draftRequests[nurseId] = state.requests.filter(function (r) { return r.nurseId === nurseId; }).map(function (r) { return { day: r.day, shift: reqShift(r) }; });
    }
    return state.draftRequests[nurseId];
  }

  function requestForDay(nurseId, day) {
    return selectedRequests(nurseId).find(function (r) { return r.day === day; });
  }

  function reqShift(r) { return r && r.shift ? r.shift : "OFF"; }

  function toggleDraftRequest(nurseId, day) {
    el.nfOffMessage.innerHTML = "";
    state.inspectDay = day;
    el.nfInspectDay.value = String(day);
    renderInspectResult();
    renderShiftChoices(nurseId, day);
  }

  function renderShiftChoices(nurseId, day) {
    var current = requestForDay(nurseId, day);
    el.nfShiftChoices.innerHTML = ["D", "E", "N", "OFF"].map(function (shift) {
      var active = current && current.shift === shift;
      return '<button type="button" class="' + (active ? 'primary ' : '') + 'small shift-choice req-' + shift + '" data-choice="' + shift + '">' + shift + '</button>';
    }).join("");
    qsa("[data-choice]", el.nfShiftChoices).forEach(function (btn) {
      btn.addEventListener("click", function () { setDraftRequest(nurseId, day, btn.getAttribute("data-choice")); });
    });
  }

  function setDraftRequest(nurseId, day, shift) {
    var reqs = selectedRequests(nurseId);
    var idx = reqs.findIndex(function (r) { return r.day === day; });
    if (idx < 0 && requestCountExcluding(nurseId, day) >= MAX_DAILY_REQUESTS) {
      el.nfOffMessage.innerHTML = msg("error", day + "\uc77c은 이미 3명이 근무를 신청했습니다. 하루에 4명 이상은 신청할 수 없습니다.");
      return;
    }
    if (idx >= 0 && reqs[idx].shift === shift) reqs.splice(idx, 1);
    else if (idx >= 0) reqs[idx].shift = shift;
    else reqs.push({ day: day, shift: shift });
    reqs.sort(function (a, b) { return a.day - b.day; });
    save();
    renderOffPanel();
    el.nfInspectDay.value = String(day);
    renderInspectResult();
    renderShiftChoices(nurseId, day);
  }

  async function submitMyRequests() {
    var nurseId = state.loginId;
    if (!nurseId) return;
    if (!requirePassword("\uadfc\ubb34 \uc2e0\uccad/\ubcc0\uacbd \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.", state.loginId)) return;
    var reqs = selectedRequests(nurseId).slice().sort(function (a, b) { return a.day - b.day; });
    var blockedDay = reqs.find(function (r) { return requestCountExcluding(nurseId, r.day) >= MAX_DAILY_REQUESTS; });
    if (blockedDay) {
      el.nfOffMessage.innerHTML = msg("error", blockedDay.day + "\uc77c은 이미 3명이 근무를 신청했습니다. 하루에 4명 이상은 신청할 수 없습니다.");
      return;
    }
    state.requests = state.requests.filter(function (r) { return r.nurseId !== nurseId; });
    reqs.forEach(function (r) { state.requests.push({ id: "r" + Date.now() + Math.random().toString(36).slice(2, 6), nurseId: nurseId, day: r.day, shift: r.shift }); });
    save();
    var ok = await saveMyRequestsToSupabase(nurseId, reqs);
    if (!ok) return;
    el.nfOffMessage.innerHTML = msg("ok", "\uadfc\ubb34 \uc2e0\uccad\uc774 \uc800\uc7a5\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
    renderAll();
  }

  function renderRequests() {
    if (!state.requests.length) {
      el.nfRequestList.innerHTML = '<div class="empty">' + TXT.noRequests + '</div>';
      return;
    }
    var grouped = {};
    state.requests.forEach(function (r) {
      if (!grouped[r.nurseId]) grouped[r.nurseId] = [];
      grouped[r.nurseId].push(r);
    });
    el.nfRequestList.innerHTML = Object.keys(grouped).sort(function (a, b) {
      return nurseName(a).localeCompare(nurseName(b), "ko");
    }).map(function (nurseId) {
      var n = nurse(nurseId);
      var items = grouped[nurseId].slice().sort(function (a, b) { return a.day - b.day || reqShift(a).localeCompare(reqShift(b)); });
      return '<div class="req-row grouped"><div class="req-person"><b>' + esc(n ? n.name : "") + '</b><span>' + (n ? ROLE_LABEL[n.role] : "") + '</span></div><div class="req-days">' + items.map(function (r) {
        return '<span class="req-chip">' + r.day + '\uc77c(' + dow(r.day) + ') ' + reqShift(r) + '<button class="mini-x" type="button" data-del="' + r.id + '" aria-label="\uc0ad\uc81c">×</button></span>';
      }).join("") + '</div></div>';
    }).join("");
    qsa("[data-del]", el.nfRequestList).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-del");
        state.requests = state.requests.filter(function (r) { return r.id !== id; });
        save(); deleteRequestFromSupabase(id); renderAll();
      });
    });
  }

  function renderPreviousUploadStatus() {
    if (!el.nfPreviousUploadStatus) return;
    if (hasPreviousSchedule()) {
      var time = state.previousUploadedAt ? new Date(state.previousUploadedAt) : null;
      var label = time && !isNaN(time.getTime()) ? time.toLocaleString("ko-KR") : "\uc2dc\uac04 \uc5c6\uc74c";
      el.nfPreviousUploadStatus.innerHTML = "\uc774\uc804\ub2ec \uadfc\ubb34\ud45c \uc5c5\ub85c\ub4dc \uc644\ub8cc: " + label;
    } else {
      el.nfPreviousUploadStatus.innerHTML = "\uc774\uc804\ub2ec \uadfc\ubb34\ud45c\uac00 \uc544\uc9c1 \uc5c5\ub85c\ub4dc\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.";
    }
  }

  async function handlePreviousExcelUpload(event) {
    var file = event.target.files && event.target.files[0];
    if (!file) return;
    if (!requirePassword("\uc774\uc804\ub2ec \uadfc\ubb34\ud45c \uc5c5\ub85c\ub4dc \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.")) {
      event.target.value = "";
      return;
    }
    try {
      var parsed = await parseFinalScheduleFile(file);
      state.previousSchedule = normalizeScheduleForCurrentNurses(parsed);
      state.previousUploadedAt = new Date().toISOString();
      save();
      renderAll();
      await saveSettingsToSupabase();
      showTransientBanner("\uc774\uc804\ub2ec \uadfc\ubb34\ud45c\uac00 \uc5c5\ub85c\ub4dc\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
    } catch (err) {
      console.error(err);
      alert("\uc774\uc804\ub2ec \uadfc\ubb34\ud45c\ub97c \uc77d\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. \uc571\uc5d0\uc11c \ub2e4\uc6b4\ub85c\ub4dc\ud55c \ud615\uc2dd\uc744 \uc720\uc9c0\ud574\uc11c \ub2e4\uc2dc \uc5c5\ub85c\ub4dc\ud574\uc8fc\uc138\uc694.");
    } finally {
      event.target.value = "";
    }
  }

  async function clearPreviousSchedule() {
    if (!hasPreviousSchedule()) return;
    if (!requirePassword("\uc774\uc804\ub2ec \uadfc\ubb34\ud45c \ucde8\uc18c \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.")) return;
    clearPreviousStateOnly();
    save();
    renderAll();
    await saveSettingsToSupabase();
    showTransientBanner("\uc774\uc804\ub2ec \uadfc\ubb34\ud45c\uac00 \ucde8\uc18c\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
  }

  function renderFinalUploadStatus() {
    if (!el.nfFinalUploadStatus) return;
    if (hasFinalSchedule()) {
      var time = state.finalizedAt ? new Date(state.finalizedAt) : null;
      var label = time && !isNaN(time.getTime()) ? time.toLocaleString("ko-KR") : "\uc2dc\uac04 \uc5c6\uc74c";
      el.nfFinalUploadStatus.innerHTML = "\ucd5c\uc885\ubcf8 \uc5c5\ub85c\ub4dc \uc644\ub8cc: " + label;
    } else {
      el.nfFinalUploadStatus.innerHTML = "\ucd5c\uc885 \uc5d1\uc140\ud30c\uc77c\uc774 \uc544\uc9c1 \uc5c5\ub85c\ub4dc\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.";
    }
  }

  async function handleFinalExcelUpload(event) {
    var file = event.target.files && event.target.files[0];
    if (!file) return;
    if (!requirePassword("\ucd5c\uc885 \uadfc\ubb34\ud45c \uc5c5\ub85c\ub4dc \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.")) {
      event.target.value = "";
      return;
    }
    try {
      var parsed = await parseFinalScheduleFile(file);
      state.finalSchedule = normalizeScheduleForCurrentNurses(parsed);
      state.schedule = normalizeScheduleForCurrentNurses(parsed);
      state.score = scoreSchedule(state.schedule);
      state.finalizedAt = new Date().toISOString();
      save();
      renderAll();
      await saveSettingsToSupabase();
      await saveScheduleToSupabase();
      showTransientBanner("\ucd5c\uc885 \uadfc\ubb34\ud45c\uac00 \uc5c5\ub85c\ub4dc\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
    } catch (err) {
      console.error(err);
      alert("\uc5d1\uc140\ud30c\uc77c\uc744 \uc77d\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. \uc571\uc5d0\uc11c \ub2e4\uc6b4\ub85c\ub4dc\ud55c \uadfc\ubb34\ud45c \ud615\uc2dd\uc744 \uc720\uc9c0\ud574\uc11c \ub2e4\uc2dc \uc5c5\ub85c\ub4dc\ud574\uc8fc\uc138\uc694.");
    } finally {
      event.target.value = "";
    }
  }

  async function clearFinalSchedule() {
    if (!hasFinalSchedule()) return;
    if (!requirePassword("\ucd5c\uc885\ubcf8 \ucde8\uc18c \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud558\uc138\uc694.")) return;
    clearFinalStateOnly();
    save();
    renderAll();
    await saveSettingsToSupabase();
    showTransientBanner("\ucd5c\uc885\ubcf8\uc774 \ucde8\uc18c\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
  }

  function clearFinalStateOnly() {
    state.finalSchedule = {};
    state.finalizedAt = "";
  }

  function clearPreviousStateOnly() {
    state.previousSchedule = {};
    state.previousUploadedAt = "";
  }

  async function parseFinalScheduleFile(file) {
    var rows;
    if (window.XLSX && /\.(xlsx|xls)$/i.test(file.name || "")) {
      var buffer = await file.arrayBuffer();
      var workbook = window.XLSX.read(buffer, { type: "array" });
      var sheet = workbook.Sheets[workbook.SheetNames[0]];
      rows = window.XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false, defval: "" });
    } else {
      var text = await file.text();
      rows = /^\s*</.test(text) ? rowsFromHtmlTable(text) : rowsFromCsv(text);
    }
    return scheduleFromRows(rows || []);
  }

  function rowsFromHtmlTable(text) {
    var doc = new DOMParser().parseFromString(text, "text/html");
    return qsa("tr", doc).map(function (tr) {
      return qsa("th,td", tr).map(function (td) { return td.textContent.trim(); });
    });
  }

  function rowsFromCsv(text) {
    return text.split(/\r?\n/).filter(Boolean).map(function (line) {
      return line.split(",").map(function (cell) { return cell.replace(/^"|"$/g, "").trim(); });
    });
  }

  function scheduleFromRows(rows) {
    var headerIndex = rows.findIndex(function (row) { return row.some(function (cell) { return String(cell).indexOf("\uc774\ub984") >= 0; }); });
    if (headerIndex < 0) throw new Error("header not found");
    var header = rows[headerIndex].map(function (v) { return String(v || "").trim(); });
    var dayCols = [];
    header.forEach(function (cell, idx) {
      var match = String(cell).match(/(\d{1,2})\s*\uc77c?/);
      if (match) dayCols.push({ day: Number(match[1]), col: idx });
    });
    if (!dayCols.length) {
      dayCols = range(daysInMonth()).map(function (day) { return { day: day, col: day + 1 }; });
    }

    var nameMap = {};
    scheduleNurses().forEach(function (n) { nameMap[n.name.replace(/\s+/g, "")] = n; });
    var out = {};
    scheduleNurses().forEach(function (n) { out[n.id] = Array(daysInMonth()).fill(""); });

    rows.slice(headerIndex + 1).forEach(function (row) {
      var name = String(row[0] || "").trim();
      var compact = name.replace(/\s+/g, "");
      var n = nameMap[compact];
      if (!n) return;
      dayCols.forEach(function (item) {
        if (item.day < 1 || item.day > daysInMonth()) return;
        out[n.id][item.day - 1] = normalizeUploadedShift(row[item.col]);
      });
    });

    var filled = Object.keys(out).some(function (id) { return out[id].some(Boolean); });
    if (!filled) throw new Error("no schedule rows");
    return out;
  }

  function normalizeUploadedShift(value) {
    var raw = String(value == null ? "" : value).trim();
    var upper = raw.toUpperCase();
    if (!raw) return "";
    if (upper === "D" || /DAY|데이/.test(upper)) return "D";
    if (upper === "E" || /EVENING|이브/.test(upper)) return "E";
    if (upper === "N" || /NIGHT|나이트/.test(upper)) return "N";
    if (upper === "OFF" || upper === "O" || /오프|휴무/.test(upper)) return "OFF";
    if (upper === "MD") return "MD";
    return upper;
  }

  function showDone() {
    showTransientBanner(TXT.done);
  }

  function showTransientBanner(text) {
    var box = el.nfDoneOverlay.querySelector(".overlay-box");
    box.textContent = text;
    el.nfDoneOverlay.classList.remove("hidden");
    clearTimeout(showTransientBanner.timer);
    showTransientBanner.timer = setTimeout(function () { el.nfDoneOverlay.classList.add("hidden"); }, 1600);
  }

  async function generateBest() {
    if (ORTOOLS_SOLVER_URL) {
      var solved = await generateWithOrTools();
      if (solved) return true;
    }
    return generateSingleBest();
    var best = null;
    var bestValid = null;
    var bestHard = null;
    var attempts = Math.max(state.tries || 0, autoTries(), 500);
    var impossible = hardImpossibleReason();
    for (var i = 0; i < attempts; i++) {
      var schedule = buildCandidate();
      var score = scoreSchedule(schedule);
      if (!best || score > best.score) best = { schedule: schedule, score: score };
      if (nightRangeOk(schedule) && (!bestValid || score > bestValid.score)) bestValid = { schedule: schedule, score: score };
      if (hardScheduleOk(schedule) && (!bestHard || score > bestHard.score)) bestHard = { schedule: schedule, score: score };
    }
    var chosen = bestHard || bestValid || best;
    state.schedule = chosen ? chosen.schedule : {};
    state.score = chosen ? chosen.score : null;
    if (impossible) {
      showTransientBanner(impossible);
    } else if (chosen && !bestHard) {
      showTransientBanner("필수 조건을 모두 만족하는 후보를 찾지 못했습니다. 신청/인원 설정을 확인해주세요.");
    }
    save();
    renderSchedule();
    validateAndRender(false);
    return !!bestHard;
  }

  async function generateWithOrTools() {
    try {
      var response = await fetch(ORTOOLS_SOLVER_URL.replace(/\/$/, "") + "/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          year: state.year,
          month: state.month,
          nurses: state.nurses,
          requests: state.requests,
          previousSchedule: state.previousSchedule,
          needs: state.needs,
          maxNeeds: state.maxNeeds,
          timeLimitSeconds: 25
        })
      });
      var result = await response.json();
      if (!response.ok || !result.ok || !result.schedule) {
        showTransientBanner(result.error || "OR-Tools 근무표 생성에 실패했습니다.");
        return false;
      }
      state.scheduleOptions = [];
      state.schedule = result.schedule;
      enforceDailyMaximums(state.schedule);
      state.score = scoreSchedule(state.schedule);
      save();
      renderSchedule();
      renderScheduleOptions();
      validateAndRender(false);
      return mandatoryScheduleOk(state.schedule);
    } catch (err) {
      console.error("OR-Tools solver error:", err);
      showTransientBanner("OR-Tools 서버 연결에 실패해 기존 방식으로 작성합니다.");
      return false;
    }
  }

  function generateSingleBest() {
    var best = null;
    var bestMandatory = null;
    var attempts = Math.max(state.tries || 0, autoTries(), 700);
    var impossible = hardImpossibleReason();
    for (var i = 0; i < attempts; i++) {
      var schedule = buildCandidate();
      repairMandatoryPriorities(schedule);
      repairNightRecovery(schedule);
      repairForbiddenPatterns(schedule);
      var score = scoreSchedule(schedule);
      var item = {
        schedule: cloneSchedule(schedule),
        score: score,
        round: 1,
        hard: mandatoryScheduleOk(schedule),
        mandatory: mandatoryViolationCount(schedule),
        errors: validationCount(schedule, "error"),
        warnings: validationCount(schedule, "warn")
      };
      if (!best || item.score > best.score) best = item;
      if (item.hard && (!bestMandatory || item.score > bestMandatory.score)) bestMandatory = item;
    }
    var chosen = bestMandatory || best;
    state.scheduleOptions = [];
    state.schedule = chosen ? cloneSchedule(chosen.schedule) : {};
    enforceDailyMaximums(state.schedule);
    state.score = Object.keys(state.schedule || {}).length ? scoreSchedule(state.schedule) : null;
    if (impossible) {
      showTransientBanner(impossible);
    } else if (chosen && !chosen.hard) {
      showTransientBanner("1\uc21c\uc704/2\uc21c\uc704 \ud544\uc218\uc870\uac74\uc744 \ubaa8\ub450 \ucda9\uc871\ud558\ub294 \uadfc\ubb34\ud45c\ub97c \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. \uc778\uc6d0/\uc694\uccad/\uc624\ud504 \uc124\uc815\uc744 \ud655\uc778\ud574\uc8fc\uc138\uc694.");
    }
    save();
    renderSchedule();
    renderScheduleOptions();
    validateAndRender(false);
    return !!(chosen && chosen.hard);
  }

  function buildCandidate() {
    var s = {};
    state.nurses.forEach(function (n) {
      s[n.id] = range(daysInMonth()).map(function (d) {
        if (n.role === "head") return isWeekend(d) ? "OFF" : "D";
        if (n.role === "edu") {
          if (dow(d) === "\uc77c") return "OFF";
          return dow(d) === "\ud1a0" ? "MD" : "D";
        }
        return "";
      });
    });
    applyHardRequests(s);
    applyPreviousMonthCarryover(s);
    var nightTargets = nightTargetCounts(s);
    assignNights(s, nightTargets);
    assignDE(s);
    fillOff(s);
    repairStaffing(s);
    balanceOffQuota(s);
    repairStaffing(s);
    repairNightStaffing(s, nightTargets);
    balanceOffQuota(s);
    finalOffBalance(s);
    applyHardRequests(s);
    forceNightMinimums(s, nightTargets);
    forcePersonalNightMinimums(s);
    repairStaffing(s);
    repairNightStaffing(s, nightTargets);
    reduceExcessOff(s);
    repairForbiddenPatterns(s);
    repairStaffing(s);
    forceOffCeiling(s);
    applyHardRequests(s);
    guaranteePersonalNightRange(s);
    rebalancePersonalNightCounts(s);
    repairStaffing(s);
    repairOverstaffing(s);
    for (var pass = 0; pass < 2; pass++) {
      guaranteePersonalNightRange(s);
      rebalancePersonalNightCounts(s);
      repairMandatoryPriorities(s);
      repairForbiddenPatterns(s);
      repairEveningOffDay(s);
      repairDayEveningBalance(s);
      repairLongWorkRuns(s);
      repairNightRecovery(s);
      repairStaffing(s);
      repairOverstaffing(s);
    }
    applyHardRequests(s);
    applyPreviousMonthCarryover(s);
    repairMandatoryPriorities(s);
    repairNightRecovery(s);
    repairForbiddenPatterns(s);
    repairEveningOffDay(s);
    repairDayEveningBalance(s);
    repairLongWorkRuns(s);
    enforceDailyMaximums(s);
    return s;
  }

  function applyHardRequests(s) {
    state.requests.forEach(function (r) {
      if (!s[r.nurseId]) return;
      var shift = reqShift(r);
      if (shift === "N") forceNightRequest(s, r);
      else if (shift === "OFF") s[r.nurseId][r.day - 1] = "OFF";
      else s[r.nurseId][r.day - 1] = shift;
    });
  }

  function applyPreviousMonthCarryover(s) {
    if (!hasPreviousSchedule()) return;
    workers().forEach(function (n) {
      previousCarryoverAssignments(n.id).forEach(function (item) {
        if (s[n.id] && item.day >= 1 && item.day <= daysInMonth()) s[n.id][item.day - 1] = item.shift;
      });
    });
  }

  function previousCarryoverAssignments(id) {
    var arr = (state.previousSchedule || {})[id] || [];
    var out = [];
    if (!arr.length) return out;
    var last = arr.length - 1;
    if (arr[last] === "N") {
      var start = last;
      while (start > 0 && arr[start - 1] === "N") start--;
      var len = last - start + 1;
      if (len === 1) {
        var targetLen = preferredNightBlockLen(id);
        var extraNights = Math.max(1, targetLen - len);
        for (var nDay = 1; nDay <= extraNights && nDay <= daysInMonth(); nDay++) out.push({ day: nDay, shift: "N" });
        for (var offDay = extraNights + 1; offDay <= extraNights + 2 && offDay <= daysInMonth(); offDay++) out.push({ day: offDay, shift: "OFF" });
      } else {
        out.push({ day: 1, shift: "OFF" });
        if (daysInMonth() >= 2) out.push({ day: 2, shift: "OFF" });
      }
      return out;
    }
    var lastN = -1;
    for (var i = last; i >= Math.max(0, arr.length - 7); i--) if (arr[i] === "N") { lastN = i; break; }
    if (lastN < 0) return out;
    var offAfter = 0;
    for (var j = lastN + 1; j < arr.length; j++) {
      if (arr[j] === "OFF") offAfter++;
      else break;
    }
    var needed = Math.max(0, 2 - offAfter);
    for (var d = 1; d <= needed && d <= daysInMonth(); d++) out.push({ day: d, shift: "OFF" });
    return out;
  }

  function previousCarryoverOffDays(id) {
    return previousCarryoverAssignments(id).filter(function (item) { return item.shift === "OFF"; }).map(function (item) { return item.day; });
  }

  function previousCarryoverNightDays(id) {
    return previousCarryoverAssignments(id).filter(function (item) { return item.shift === "N"; }).map(function (item) { return item.day; });
  }

  function isCarryoverOff(id, day) {
    return previousCarryoverOffDays(id).indexOf(day) >= 0;
  }

  function isCarryoverNight(id, day) {
    return previousCarryoverNightDays(id).indexOf(day) >= 0;
  }

  function previousEndingNightRunLength(id) {
    var arr = (state.previousSchedule || {})[id] || [];
    if (!arr.length || arr[arr.length - 1] !== "N") return 0;
    var len = 0;
    for (var i = arr.length - 1; i >= 0 && arr[i] === "N"; i--) len++;
    return len;
  }

  function forceNightRequest(s, r) {
    var id = r.nurseId;
    var day = r.day;
    var len = preferredNightBlockLen(id);
    var starts = range(len).map(function (offset) { return day - offset; }).filter(function (start) { return start >= 1 && start + len - 1 <= daysInMonth() && day >= start && day <= start + len - 1; });
    var start = starts.find(function (st) { return canForceNightBlock(s, id, st, len); });
    if (!start) {
      s[id][day - 1] = "N";
      return;
    }
    for (var i = 0; i < len; i++) s[id][start - 1 + i] = "N";
    for (var j = len; j < len + 2 && start - 1 + j < daysInMonth(); j++) {
      var offDay = start + j;
      if (!hasRequest(id, offDay)) s[id][offDay - 1] = "OFF";
    }
  }

  function canForceNightBlock(s, id, start, len) {
    for (var i = 0; i < len; i++) {
      var day = start + i;
      var locked = requestShiftFor(id, day);
      if (locked && locked !== "N") return false;
    }
    return true;
  }

  function applyShiftRequests(s) {
    state.requests.forEach(function (r) {
      if (!s[r.nurseId] || reqShift(r) === "OFF") return;
      if (reqShift(r) === "N") {
        var len = preferredNightBlockLen(r.nurseId);
        if (canNight(s, r.nurseId, r.day, len)) placeNightBlock(s, r.nurseId, r.day, len);
      } else if (canShift(s, r.nurseId, r.day, reqShift(r))) {
        s[r.nurseId][r.day - 1] = reqShift(r);
      }
    });
  }

  function assignNights(s, targets) {
    var guard = 0;
    while (deficientNightDay(s) && guard++ < daysInMonth() * workers().length * 8) {
      var d = deficientNightDay(s);
      var block = pickNightBlock(s, d, targets);
      if (!block) break;
      placeNightBlock(s, block.nurse.id, block.start, block.len);
    }
  }

  function forceNightMinimums(s, targets) {
    var guard = 0;
    while (deficientNightDay(s) && guard++ < daysInMonth() * workers().length * 4) {
      var d = deficientNightDay(s);
      var opt = pickForceNightOption(s, d, targets);
      if (!opt) break;
      placeNightBlock(s, opt.nurse.id, opt.start, opt.len || preferredNightBlockLen(opt.nurse.id));
    }
  }

  function forcePersonalNightMinimums(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (countNurse(s, n.id, "N") < 5 && guard++ < daysInMonth() * 2) {
        var opt = pickForceNightForNurse(s, n.id);
        if (!opt) break;
        placeNightBlock(s, n.id, opt.start, opt.len || preferredNightBlockLen(n.id));
      }
    });
  }

  function pickForceNightForNurse(s, id) {
    var len = preferredNightBlockLen(id);
    var starts = shuffle(range(daysInMonth() - len + 1)).filter(function (start) {
      return canForceNightMinimum(s, id, start, len);
    });
    starts.sort(function (a, b) {
      return countDay(s, a, "N") + countDay(s, a + 1, "N") - countDay(s, b, "N") - countDay(s, b + 1, "N") + Math.random() * .3;
    });
    return starts.length ? { start: starts[0], len: len } : null;
  }

  function pickForceNightOption(s, day, targets) {
    var options = [];
    workers().forEach(function (n) {
      var len = preferredNightBlockLen(n.id);
      range(len).map(function (offset) { return day - offset; }).forEach(function (start) {
        if (canForceNightMinimum(s, n.id, start, len, targets)) options.push({ nurse: n, start: start, len: len });
      });
    });
    options.sort(function (a, b) {
      return forceNightScore(s, a, day) - forceNightScore(s, b, day) + Math.random() * .25;
    });
    return options[0] || null;
  }

  function forceNightScore(s, opt, day) {
    var n = opt.nurse;
    var score = countNurse(s, n.id, "N") * 8 + workCount(s, n.id);
    if (n.role === "charge" && countRoleDay(s, day, "N", "charge") < 1) score -= 20;
    if (n.role === "mid" && countRoleDay(s, day, "N", "mid") < 2) score -= 16;
    if (n.role === "newn" && countRoleDay(s, day, "N", "newn") >= 4) score += 12;
    return score;
  }

  function canForceNightMinimum(s, id, start, len, targets) {
    if (start < 1 || start + len - 1 > daysInMonth()) return false;
    if (countNurse(s, id, "N") + len > ((targets || {})[id] || 7)) return false;
    var arr = s[id];
    if (arr[start - 2] === "N" || arr[start - 1 + len] === "N") return false;
    if (nightCooldown(arr, start - 1)) return false;
    if (nightCooldownAfter(arr, start - 1, len)) return false;
    for (var i = 0; i < len; i++) {
      var day = start + i;
      if (hasRequest(id, day) && requestShiftFor(id, day) !== "N") return false;
      if (arr[day - 1] === "N") return false;
      if (countDay(s, day, "N") >= maxNeed("N")) return false;
      if (avoidPairConflict(s, id, day)) return false;
      if (!roleLimitOk(s, id, day, "N")) return false;
    }
    for (var j = len; j < len + 2 && start - 1 + j < daysInMonth(); j++) {
      var offDay = start + j;
      if (hasRequest(id, offDay) && requestShiftFor(id, offDay) !== "OFF") return false;
      if (arr[offDay - 1] === "N") return false;
    }
    var old = [];
    for (var o = 0; o < len; o++) old.push(arr[start - 1 + o]);
    for (var k = 0; k < len; k++) arr[start - 1 + k] = "N";
    var ok = maxWork(arr) <= 4;
    for (var z = 0; z < len; z++) arr[start - 1 + z] = old[z];
    return ok;
  }

  function placeNightBlock(s, id, start, len) {
    for (var x = 0; x < len; x++) s[id][start - 1 + x] = "N";
    for (var y = len; y < len + 2 && start - 1 + y < daysInMonth(); y++) {
      var day = start + y;
      if (!hasRequest(id, day) || requestShiftFor(id, day) === "OFF") s[id][start - 1 + y] = "OFF";
    }
  }

  function deficientNightDay(s) {
    var days = range(daysInMonth()).filter(function (d) { return countDay(s, d, "N") < need("N"); });
    if (!days.length) return null;
    days.sort(function (a, b) { return countDay(s, a, "N") - countDay(s, b, "N") || Math.random() - .5; });
    return days[0];
  }

  function pickNightBlock(s, day, targets) {
    var options = [];
    workers().forEach(function (n) {
      [preferredNightBlockLen(n.id)].forEach(function (len) {
        for (var start = day - len + 1; start <= day; start++) {
          if (start < 1 || start + len - 1 > daysInMonth()) continue;
          if (canNight(s, n.id, start, len, targets)) options.push({ nurse: n, start: start, len: len });
        }
      });
    });
    options.sort(function (a, b) {
      return nightOptionScore(s, a, day) - nightOptionScore(s, b, day) + Math.random() * .3;
    });
    return options[0] || null;
  }

  function nightOptionScore(s, opt, focusDay) {
    var score = Math.abs((countNurse(s, opt.nurse.id, "N") + opt.len) - 6) * 4 + (opt.len === 3 ? 18 : 0);
    for (var i = 0; i < opt.len; i++) if (avoidPairSoftConflict(s, opt.nurse.id, opt.start + i)) score += 1;
    if (opt.nurse.role === "charge" && countRoleDay(s, focusDay, "N", "charge") < 1) score -= 8;
    if (opt.nurse.role === "charge" && countRoleDay(s, focusDay, "N", "charge") >= 1) score += 80;
    if (opt.nurse.role === "mid" && countRoleDay(s, focusDay, "N", "mid") < 2) score -= 6;
    if (opt.nurse.role === "newn" && countRoleDay(s, focusDay, "N", "charge") < 1) score += 5;
    return score;
  }

  function assignDE(s) {
    range(daysInMonth()).forEach(function (d) {
      ["D", "E"].forEach(function (shift) {
        [["charge", 1], ["mid", 3], ["newn", 3]].forEach(function (target) {
          while (countRoleDay(s, d, shift, target[0]) < target[1] && countDay(s, d, shift) < need(shift)) {
            var n = pickShift(s, d, shift, target[0]);
            if (!n) break;
            s[n.id][d - 1] = shift;
          }
        });
        while (countDay(s, d, shift) < need(shift)) {
          var any = pickShift(s, d, shift, null);
          if (!any) break;
          s[any.id][d - 1] = shift;
        }
      });
    });
  }

  function pickShift(s, day, shift, role) {
    return shuffle(workers()).filter(function (n) { return (!role || n.role === role) && canShift(s, n.id, day, shift); }).sort(function (a, b) {
      return shiftBalanceScore(s, a.id, shift) - shiftBalanceScore(s, b.id, shift) ||
        workCount(s, a.id) - workCount(s, b.id) ||
        (avoidPairSoftConflict(s, a.id, day) ? 1 : 0) - (avoidPairSoftConflict(s, b.id, day) ? 1 : 0) ||
        Math.random() * .4;
    })[0] || null;
  }

  function fillOff(s) {
    workers().forEach(function (n) {
      s[n.id].forEach(function (v, i) { if (!v) s[n.id][i] = "OFF"; });
    });
  }

  function repairNightStaffing(s, targets) {
    assignNights(s, targets);
  }

  function repairStaffing(s) {
    range(daysInMonth()).forEach(function (d) {
      ["D", "E", "N"].forEach(function (shift) {
        var guard = 0;
        while (countDay(s, d, shift) < need(shift) && guard++ < workers().length * 2) {
          var n = pickFromOff(s, d, shift);
          if (!n) break;
          s[n.id][d - 1] = shift;
        }
      });
    });
  }

  function repairOverstaffing(s) {
    trimOverstaffing(s, false);
  }

  function enforceDailyMaximums(s) {
    trimOverstaffing(s, false);
    trimOverstaffing(s, true);
  }

  function trimOverstaffing(s, allowRequested) {
    range(daysInMonth()).forEach(function (d) {
      ["D", "E", "N"].forEach(function (shift) {
        var guard = 0;
        while (countDay(s, d, shift) > maxNeed(shift) && guard++ < workers().length * 2) {
          var n = pickOverstaffedNurse(s, d, shift, allowRequested);
          if (!n) break;
          s[n.id][d - 1] = "OFF";
        }
      });
    });
  }

  function pickOverstaffedNurse(s, day, shift, allowRequested) {
    var candidates = workers().filter(function (n) {
      if ((s[n.id] || [])[day - 1] !== shift) return false;
      if (shift === "N" && isCarryoverNight(n.id, day)) return false;
      if (hasRequest(n.id, day) && !allowRequested) return false;
      return true;
    });
    candidates.sort(function (a, b) {
      return countNurse(s, b.id, shift) - countNurse(s, a.id, shift) ||
        countNurse(s, a.id, "OFF") - countNurse(s, b.id, "OFF") ||
        Math.random() - .5;
    });
    return candidates[0] || null;
  }

  function balanceOffQuota(s) {
    var quota = offQuota();
    workers().forEach(function (n) {
      var guard = 0;
      while (countNurse(s, n.id, "OFF") > maxOffAllowed() && guard++ < daysInMonth() * 2) {
        var move = shuffle(range(daysInMonth())).map(function (d) {
          return { day: d, shift: shiftForOffToWork(s, n.id, d, false) };
        }).find(function (x) {
          return x.shift;
        });
        if (!move) break;
        s[n.id][move.day - 1] = move.shift;
      }
      guard = 0;
      while (false && countNurse(s, n.id, "OFF") < minOffAllowed() && guard++ < daysInMonth() * 2) {
        var cutDay = shuffle(range(daysInMonth())).find(function (d) {
          var v = (s[n.id] || [])[d - 1];
          if (hasRequest(n.id, d)) return false;
          return (v === "D" || v === "E") && countDay(s, d, v) > need(v);
        });
        if (!cutDay) break;
        s[n.id][cutDay - 1] = "OFF";
      }
    });
  }

  function finalOffBalance(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (countNurse(s, n.id, "OFF") > maxOffAllowed() && guard++ < daysInMonth() * 3) {
        var move = pickOffToWork(s, n.id);
        if (!move) break;
        s[n.id][move.day - 1] = move.shift;
      }
      guard = 0;
      while (false && countNurse(s, n.id, "OFF") < minOffAllowed() && guard++ < daysInMonth() * 3) {
        var workDay = pickWorkToOff(s, n.id);
        if (!workDay) break;
        s[n.id][workDay - 1] = "OFF";
        repairStaffing(s);
        repairNightStaffing(s);
      }
    });
  }

  function pickOffToWork(s, id) {
    var mustCut = countNurse(s, id, "OFF") > maxOffAllowed();
    var days = range(daysInMonth()).filter(function (d) { return (s[id] || [])[d - 1] === "OFF" && !hasRequest(id, d) && !isCarryoverOff(id, d) && !isNightRecoveryOff(s, id, d); });
    days.sort(function (a, b) {
      return (hasRequest(id, a) ? 1 : 0) - (hasRequest(id, b) ? 1 : 0) || offRunPenaltyAfterWork(s, id, b) - offRunPenaltyAfterWork(s, id, a) || Math.random() - .5;
    });
    var day = days.find(function (d) { return !!shiftForOffToWork(s, id, d, mustCut); });
    return day ? { day: day, shift: shiftForOffToWork(s, id, day, mustCut) } : null;
  }

  function shiftForOffToWork(s, id, day, allowRequested) {
    if ((s[id] || [])[day - 1] !== "OFF") return "";
    if (isCarryoverOff(id, day)) return "";
    if (isNightRecoveryOff(s, id, day)) return "";
    if (hasRequest(id, day) && !allowRequested) return "";
    var shifts = ["D", "E"].sort(function (a, b) {
      return shiftBalanceScore(s, id, a) - shiftBalanceScore(s, id, b) || countDay(s, day, a) - countDay(s, day, b);
    });
    for (var i = 0; i < shifts.length; i++) {
      var shift = shifts[i];
      s[id][day - 1] = "";
      var ok = allowRequested ? canShiftForOffReduction(s, id, day, shift) : canShift(s, id, day, shift);
      s[id][day - 1] = "OFF";
      if (ok) return shift;
    }
    return "";
  }

  function canShiftForOffReduction(s, id, day, shift) {
    var arr = s[id], idx = day - 1;
    if (arr[idx]) return false;
    if (countDay(s, day, shift) >= maxNeed(shift)) return false;
    if (avoidPairConflict(s, id, day)) return false;
    if (!roleLimitOk(s, id, day, shift)) return false;
    if (shift === "D" && arr[idx - 1] === "E") return false;
    if (nightRecovery(arr, idx)) return false;
    arr[idx] = shift;
    var ok = maxWork(arr) <= 4;
    arr[idx] = "";
    return ok;
  }

  function reduceExcessOff(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (countNurse(s, n.id, "OFF") > maxOffAllowed() && guard++ < daysInMonth() * 3) {
        var move = pickOffToWork(s, n.id);
        if (!move) break;
        s[n.id][move.day - 1] = move.shift;
      }
    });
  }

  function repairForbiddenPatterns(s) {
    workers().forEach(function (n) {
      var arr = s[n.id] || [];
      for (var d = 1; d < daysInMonth(); d++) {
        if (arr[d - 1] !== "E" || arr[d] !== "D") continue;
        if (hasRequest(n.id, d) || hasRequest(n.id, d + 1)) continue;
        if (countDay(s, d + 1, "D") > need("D")) {
          arr[d] = "OFF";
        } else if (countDay(s, d, "E") > need("E")) {
          arr[d - 1] = "OFF";
        } else {
          arr[d] = "";
          if (canShift(s, n.id, d + 1, "E")) arr[d] = "E";
          else arr[d] = "OFF";
        }
      }
    });
  }

  function repairMandatoryPriorities(s) {
    for (var pass = 0; pass < 3; pass++) {
      repairShortNightBlocks(s);
      repairLongNightBlocks(s);
      repairNightRecovery(s);
      repairForbiddenPatterns(s);
      forcePersonalNightMinimums(s);
      trimExcessNights(s);
      repairNightRecovery(s);
    }
  }

  function repairShortNightBlocks(s) {
    workers().forEach(function (n) {
      var arr = s[n.id] || [];
      for (var i = 0; i < daysInMonth(); i++) {
        if (arr[i] !== "N" || arr[i - 1] === "N" || arr[i + 1] === "N") continue;
        var day = i + 1;
        if (canPromoteNight(s, n.id, day + 1)) {
          arr[i + 1] = "N";
        } else if (canPromoteNight(s, n.id, day - 1)) {
          arr[i - 1] = "N";
        } else if (!hasRequest(n.id, day) && countNurse(s, n.id, "N") > 5) {
          arr[i] = "OFF";
        }
      }
    });
  }

  function repairLongNightBlocks(s) {
    workers().forEach(function (n) {
      var arr = s[n.id] || [];
      for (var i = 0; i < daysInMonth(); i++) {
        if (arr[i] !== "N" || arr[i - 1] === "N") continue;
        var len = 0;
        while (arr[i + len] === "N") len++;
        for (var cut = 3; cut < len; cut++) {
          var day = i + cut + 1;
          if (!hasRequest(n.id, day)) arr[i + cut] = "OFF";
        }
      }
    });
  }

  function trimExcessNights(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (countNurse(s, n.id, "N") > 7 && guard++ < daysInMonth()) {
        var removed = removeOneExcessNight(s, n.id);
        if (!removed) break;
      }
    });
  }

  function removeOneExcessNight(s, id) {
    var arr = s[id] || [];
    for (var i = daysInMonth() - 1; i >= 0; i--) {
      if (arr[i] !== "N" || hasRequest(id, i + 1)) continue;
      var start = i;
      while (start > 0 && arr[start - 1] === "N") start--;
      var end = i;
      while (end + 1 < daysInMonth() && arr[end + 1] === "N") end++;
      var len = end - start + 1;
      if (len === 3) {
        arr[end] = "OFF";
        return true;
      }
      if (len === 2 && countNurse(s, id, "N") >= 7 && !hasRequest(id, start + 1) && !hasRequest(id, end + 1)) {
        arr[start] = "OFF";
        arr[end] = "OFF";
        return true;
      }
    }
    return false;
  }

  function canPromoteNight(s, id, day) {
    if (day < 1 || day > daysInMonth()) return false;
    var arr = s[id] || [];
    if (hasRequest(id, day) && requestShiftFor(id, day) !== "N") return false;
    if (arr[day - 1] === "N") return false;
    if (countNurse(s, id, "N") >= 7) return false;
    if (countDay(s, day, "N") >= maxNeed("N")) return false;
    if (avoidPairConflict(s, id, day)) return false;
    return true;
  }

  function forceOffCeiling(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (countNurse(s, n.id, "OFF") > maxOffAllowed() && guard++ < daysInMonth() * 2) {
        var day = pickAnyOffDayToWork(s, n.id);
        if (!day) break;
        var shift = bestForcedShift(s, n.id, day);
        s[n.id][day - 1] = "";
        if (canShift(s, n.id, day, shift)) {
          s[n.id][day - 1] = shift;
        } else {
          var alt = shift === "D" ? "E" : "D";
          if (canShift(s, n.id, day, alt)) s[n.id][day - 1] = alt;
          else s[n.id][day - 1] = "OFF";
        }
      }
    });
  }

  function pickAnyOffDayToWork(s, id) {
    var days = range(daysInMonth()).filter(function (d) { return (s[id] || [])[d - 1] === "OFF" && !isCarryoverOff(id, d) && !isNightRecoveryOff(s, id, d); });
    days.sort(function (a, b) {
      return (hasRequest(id, a) ? 1 : 0) - (hasRequest(id, b) ? 1 : 0) || Math.random() - .5;
    });
    return days[0] || null;
  }

  function bestForcedShift(s, id, day) {
    var arr = s[id] || [];
    if (arr[day - 2] === "E") return "E";
    if (shiftBalanceScore(s, id, "D") !== shiftBalanceScore(s, id, "E")) {
      return shiftBalanceScore(s, id, "D") < shiftBalanceScore(s, id, "E") ? "D" : "E";
    }
    return countDay(s, day, "D") <= countDay(s, day, "E") ? "D" : "E";
  }

  function pickWorkToOff(s, id) {
    var days = range(daysInMonth()).filter(function (d) {
      var v = (s[id] || [])[d - 1];
      if (hasRequest(id, d)) return false;
      return (v === "D" || v === "E") && countDay(s, d, v) > need(v);
    });
    days.sort(function (a, b) { return (hasRequest(id, b) ? 1 : 0) - (hasRequest(id, a) ? 1 : 0) || Math.random() - .5; });
    return days[0] || null;
  }

  function bestWorkShiftForDay(s, day) {
    return countDay(s, day, "D") <= countDay(s, day, "E") ? "D" : "E";
  }

  function offRunPenaltyAfterWork(s, id, day) {
    var arr = (s[id] || []).slice();
    arr[day - 1] = "D";
    return offTripleBlocks(arr);
  }

  function pickFromOff(s, day, shift) {
    return shuffle(workers()).filter(function (n) {
      if ((s[n.id] || [])[day - 1] !== "OFF") return false;
      if (isCarryoverOff(n.id, day)) return false;
      if (isNightRecoveryOff(s, n.id, day)) return false;
      if (hasRequest(n.id, day)) return false;
      if (countNurse(s, n.id, "OFF") <= 0) return false;
      s[n.id][day - 1] = "";
      var ok = canShift(s, n.id, day, shift);
      s[n.id][day - 1] = "OFF";
      return ok;
    }).sort(function (a, b) {
      return offReduction(s, a.id) - offReduction(s, b.id) + workCount(s, a.id) - workCount(s, b.id) + Math.random() * .3;
    })[0] || null;
  }

  function offReduction(s, id) {
    return Math.max(0, offQuota() - countNurse(s, id, "OFF"));
  }

  function canNight(s, id, day, len, targets) {
    if (day + len - 1 > daysInMonth()) return false;
    if (len !== preferredNightBlockLen(id)) return false;
    if (countNurse(s, id, "N") + len > ((targets || {})[id] || 7)) return false;
    if (s[id][day - 2] === "N") return false;
    if (nightCooldown(s[id], day - 1)) return false;
    if (nightCooldownAfter(s[id], day - 1, len)) return false;
    for (var i = 0; i < len; i++) {
      if (s[id][day - 1 + i]) return false;
      if (countDay(s, day + i, "N") >= need("N")) return false;
      if (countDay(s, day + i, "N") >= maxNeed("N")) return false;
      if (avoidPairConflict(s, id, day + i)) return false;
      if (!roleLimitOk(s, id, day + i, "N")) return false;
    }
    for (var j = len; j < len + 2 && day - 1 + j < daysInMonth(); j++) if (s[id][day - 1 + j] && s[id][day - 1 + j] !== "OFF") return false;
    for (var k = 0; k < len; k++) s[id][day - 1 + k] = "N";
    var ok = maxWork(s[id]) <= 4;
    for (var z = 0; z < len; z++) s[id][day - 1 + z] = "";
    return ok;
  }

  function canShift(s, id, day, shift) {
    var arr = s[id], idx = day - 1;
    if (arr[idx]) return false;
    if (countDay(s, day, shift) >= maxNeed(shift)) return false;
    if (avoidPairConflict(s, id, day)) return false;
    if (!roleLimitOk(s, id, day, shift)) return false;
    if (shift === "D" && arr[idx - 1] === "E") return false;
    if (nightRecovery(arr, idx)) return false;
    arr[idx] = shift;
    var ok = maxWork(arr) <= 4;
    arr[idx] = "";
    return ok;
  }

  function roleLimitOk(s, id, day, shift) {
    return true;
  }

  function avoidPairConflict(s, id, day) {
    return false;
  }

  function avoidPairSoftConflict(s, id, day) {
    var me = nurse(id);
    if (!me) return false;
    return AVOID_PAIRS.some(function (pair) {
      if (pair.indexOf(me.name) < 0) return false;
      var otherName = pair[0] === me.name ? pair[1] : pair[0];
      var other = workers().find(function (n) { return n.name === otherName; });
      if (!other) return false;
      return isWorkValue((s[other.id] || [])[day - 1]);
    });
  }

  function isWorkValue(v) {
    return v === "D" || v === "E" || v === "N";
  }

  function nightRecovery(arr, idx) {
    return arr[idx - 1] === "N" || (arr[idx - 1] === "OFF" && arr[idx - 2] === "N");
  }

  function nightCooldown(arr, idx) {
    for (var i = 1; i <= 5; i++) if (arr[idx - i] === "N") return true;
    return false;
  }

  function nightCooldownAfter(arr, idx, len) {
    for (var i = len; i < len + 5; i++) if (arr[idx + i] === "N") return true;
    return false;
  }

  function renderSchedule() {
    el.nfScore.textContent = state.score == null ? "\uc810\uc218 \uc5c6\uc74c" : "\uc810\uc218 " + Math.round(state.score);
    if (!Object.keys(state.schedule || {}).length) {
      el.nfSchedule.innerHTML = '<div class="empty">' + TXT.noSchedule + '</div>';
      return;
    }
    var head = '<tr><th class="sticky">\uc774\ub984</th>' + range(daysInMonth()).map(function (d) {
      return '<th class="' + dayClass(d) + '">' + d + '<span class="dow">' + dow(d) + '</span></th>';
    }).join("") + '</tr>';
    var body = scheduleNurses().map(function (n) {
      var arr = state.schedule[n.id] || [];
      return '<tr><th class="sticky">' + esc(n.name) + '<span class="role">' + ROLE_LABEL[n.role] + '</span></th>' + arr.map(function (v, i) {
        return '<td class="cell s-' + v + ' ' + dayClass(i + 1) + '" data-cell="' + n.id + '" data-day="' + (i + 1) + '">' + v + '</td>';
      }).join("") + '</tr>';
    }).join("");
    el.nfSchedule.innerHTML = '<div class="scroll"><table><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>';
    qsa("[data-cell]", el.nfSchedule).forEach(function (td) {
      td.addEventListener("click", function () {
        var id = td.getAttribute("data-cell"), n = nurse(id);
        if (!n || n.role === "head" || n.role === "edu") return;
        var day = Number(td.getAttribute("data-day"));
        var cur = state.schedule[id][day - 1] || "OFF";
        state.schedule[id][day - 1] = SHIFT_CYCLE[(SHIFT_CYCLE.indexOf(cur) + 1) % SHIFT_CYCLE.length];
        state.score = scoreSchedule(state.schedule);
        save(); renderSchedule(); validateAndRender(false); saveScheduleToSupabase();
      });
    });
  }

  function renderScheduleOptions() {
    if (!el.nfScheduleOptions) return;
    if (!Object.keys(state.schedule || {}).length) {
      el.nfScheduleOptions.innerHTML = '<div class="empty">\uadfc\ubb34\ud45c \uc790\ub3d9 \uc791\uc131 \ud6c4 \uc810\uc218\uc640 \ud544\uc218\uc870\uac74 \ucda9\uc871 \uc5ec\ubd80\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4.</div>';
      return;
    }
    var mandatory = mandatoryViolationCount(state.schedule);
    var errors = validationCount(state.schedule, "error");
    var warnings = validationCount(state.schedule, "warn");
    el.nfScheduleOptions.innerHTML = '<div class="option-row active">' +
        '<div><b>\ud604\uc7ac \uadfc\ubb34\ud45c</b><span>\uc810\uc218 ' + Math.round(scoreSchedule(state.schedule)) + ' / 1\uc21c\uc704\u00b72\uc21c\uc704 \uc704\ubc18 ' + mandatory + '\uac1c / \uc624\ub958 ' + errors + '\uac1c / \uacbd\uace0 ' + warnings + '\uac1c</span></div>' +
        '<strong class="' + (mandatory ? 'danger-text' : 'ok-text') + '">' + (mandatory ? '\ud544\uc218\uc870\uac74 \ubbf8\ucda9\uc871' : '\ud544\uc218\uc870\uac74 \ucda9\uc871') + '</strong>' +
      '</div>';
  }

  function validateAndRender(doSave) {
    var messages = validate(state.schedule || {});
    if (Object.keys(state.schedule || {}).length) state.score = scoreSchedule(state.schedule);
    if (doSave !== false) save();
    el.nfScore.textContent = state.score == null ? "\uc810\uc218 \uc5c6\uc74c" : "\uc810\uc218 " + Math.round(state.score);
    if (!el.nfValidation) return;
    el.nfValidation.innerHTML = messages.length ? messages.map(function (m) { return msg(m.type, m.text); }).join("") : msg("ok", TXT.ok);
  }

  function guaranteePersonalNightRange(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (countNurse(s, n.id, "N") < 5 && guard++ < daysInMonth()) {
        var len = preferredNightBlockLen(n.id);
        var start = pickGuaranteedNightStart(s, n.id, len);
        if (!start) break;
        placeGuaranteedNightBlock(s, n.id, start, len);
      }
    });
  }

  function repairNightRecovery(s) {
    workers().forEach(function (n) {
      var arr = s[n.id] || [];
      for (var i = 0; i < daysInMonth(); i++) {
        if (arr[i] !== "N") continue;
        if (arr[i + 1] === "N") continue;
        for (var off = 1; off <= 2; off++) {
          var idx = i + off;
          if (idx < daysInMonth() && (!hasRequest(n.id, idx + 1) || requestShiftFor(n.id, idx + 1) === "OFF")) {
            arr[idx] = "OFF";
          }
        }
      }
    });
  }

  function isNightRecoveryOff(s, id, day) {
    var arr = (s[id] || []);
    var idx = day - 1;
    if (arr[idx] !== "OFF") return false;
    return arr[idx - 1] === "N" || (arr[idx - 1] === "OFF" && arr[idx - 2] === "N");
  }

  function repairEveningOffDay(s) {
    workers().forEach(function (n) {
      var arr = s[n.id] || [];
      for (var d = 1; d <= daysInMonth() - 2; d++) {
        if (arr[d - 1] !== "E" || arr[d] !== "OFF" || arr[d + 1] !== "D") continue;
        if (hasRequest(n.id, d + 2)) continue;
        if (countDay(s, d + 2, "D") > need("D")) {
          arr[d + 1] = "";
          if (countDay(s, d + 2, "E") < maxNeed("E") && canShift(s, n.id, d + 2, "E")) arr[d + 1] = "E";
          else arr[d + 1] = "D";
        }
      }
    });
  }

  function repairDayEveningBalance(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (!dayEveningBalanceOk(s, n.id) && guard++ < daysInMonth()) {
        var dCnt = countNurse(s, n.id, "D");
        var eCnt = countNurse(s, n.id, "E");
        var from = dCnt > eCnt ? "D" : "E";
        var to = from === "D" ? "E" : "D";
        var days = range(daysInMonth()).filter(function (d) {
          return (s[n.id] || [])[d - 1] === from && !hasRequest(n.id, d) && countDay(s, d, from) > need(from);
        });
        days.sort(function (a, b) {
          return countDay(s, a, to) - countDay(s, b, to) || Math.random() - .5;
        });
        var changed = days.some(function (day) {
          s[n.id][day - 1] = "";
          if (canShift(s, n.id, day, to)) {
            s[n.id][day - 1] = to;
            return true;
          }
          s[n.id][day - 1] = from;
          return false;
        });
        if (!changed) break;
      }
    });
  }

  function repairLongWorkRuns(s) {
    workers().forEach(function (n) {
      var guard = 0;
      while (maxWork(s[n.id]) > 4 && guard++ < daysInMonth()) {
        var run = firstLongWorkRun(s[n.id]);
        if (!run) break;
        var days = [];
        for (var d = run.start; d <= run.end; d++) days.push(d);
        days.sort(function (a, b) {
          return Math.abs(a - (run.start + run.end) / 2) - Math.abs(b - (run.start + run.end) / 2);
        });
        var cut = days.find(function (day) {
          var v = (s[n.id] || [])[day - 1];
          return (v === "D" || v === "E") && !hasRequest(n.id, day) && countDay(s, day, v) > need(v);
        });
        if (!cut) break;
        s[n.id][cut - 1] = "OFF";
      }
    });
  }

  function firstLongWorkRun(arr) {
    var start = 0;
    var len = 0;
    for (var i = 0; i < daysInMonth(); i++) {
      if (isWorkValue((arr || [])[i])) {
        if (!len) start = i + 1;
        len++;
        if (len > 4) return { start: start, end: i + 1 };
      } else {
        len = 0;
      }
    }
    return null;
  }

  function pickGuaranteedNightStart(s, id, len) {
    var starts = range(daysInMonth() - len + 1).filter(function (start) {
      return canGuaranteeNightBlock(s, id, start, len);
    });
    starts.sort(function (a, b) {
      return guaranteedNightStartScore(s, a, len) - guaranteedNightStartScore(s, b, len) + Math.random() * .2;
    });
    return starts[0] || null;
  }

  function canGuaranteeNightBlock(s, id, start, len) {
    if (countNurse(s, id, "N") + len > 7) return false;
    var arr = s[id] || [];
    if (arr[start - 2] === "N" || arr[start - 1 + len] === "N") return false;
    if (nightCooldown(arr, start - 1)) return false;
    if (nightCooldownAfter(arr, start - 1, len)) return false;
    for (var i = 0; i < len; i++) {
      var day = start + i;
      var locked = requestShiftFor(id, day);
      if (locked && locked !== "N") return false;
      if (arr[day - 1] === "N") return false;
      if (countDay(s, day, "N") >= maxNeed("N")) return false;
      if (avoidPairConflict(s, id, day)) return false;
    }
    for (var j = len; j < len + 2 && start - 1 + j < daysInMonth(); j++) {
      var offDay = start + j;
      if (hasRequest(id, offDay) && requestShiftFor(id, offDay) !== "OFF") return false;
      if (arr[offDay - 1] === "N") return false;
    }
    var old = [];
    for (var k = 0; k < len; k++) {
      old.push(arr[start - 1 + k]);
      arr[start - 1 + k] = "N";
    }
    var ok = maxWork(arr) <= 4;
    for (var z = 0; z < len; z++) arr[start - 1 + z] = old[z];
    return ok;
  }

  function guaranteedNightStartScore(s, start, len) {
    var score = 0;
    for (var i = 0; i < len; i++) score += countDay(s, start + i, "N") * 20;
    return score;
  }

  function placeGuaranteedNightBlock(s, id, start, len) {
    for (var i = 0; i < len; i++) s[id][start - 1 + i] = "N";
    for (var j = len; j < len + 2 && start - 1 + j < daysInMonth(); j++) {
      var day = start + j;
      if (!hasRequest(id, day) || requestShiftFor(id, day) === "OFF") s[id][day - 1] = "OFF";
    }
  }

  function rebalancePersonalNightCounts(s) {
    var guard = 0;
    while (nightUnderfilledNurses(s).length && guard++ < workers().length * daysInMonth()) {
      var low = nightUnderfilledNurses(s)[0];
      var move = pickNightTransfer(s, low.id);
      if (!move) break;
      applyNightTransfer(s, move);
    }
  }

  function nightUnderfilledNurses(s) {
    return workers().filter(function (n) { return countNurse(s, n.id, "N") < 5; }).sort(function (a, b) {
      return countNurse(s, a.id, "N") - countNurse(s, b.id, "N");
    });
  }

  function pickNightTransfer(s, receiverId) {
    var receiverNeed = 5 - countNurse(s, receiverId, "N");
    var options = [];
    workers().forEach(function (donor) {
      if (donor.id === receiverId) return;
      nightBlocks(s[donor.id] || []).forEach(function (block) {
        if (countNurse(s, donor.id, "N") - block.len < 5) return;
        if (countNurse(s, receiverId, "N") + block.len > 7) return;
        if (canReceiveNightTransfer(s, receiverId, donor.id, block.start, block.len)) {
          options.push({ receiverId: receiverId, donorId: donor.id, start: block.start, len: block.len });
        }
      });
    });
    options.sort(function (a, b) {
      return Math.abs(a.len - receiverNeed) - Math.abs(b.len - receiverNeed) || countNurse(s, b.donorId, "N") - countNurse(s, a.donorId, "N");
    });
    return options[0] || null;
  }

  function nightBlocks(arr) {
    var blocks = [];
    for (var i = 0; i < daysInMonth(); i++) {
      if (arr[i] !== "N" || arr[i - 1] === "N") continue;
      var len = 0;
      while (arr[i + len] === "N") len++;
      if (len >= 2 && len <= 3) blocks.push({ start: i + 1, len: len });
    }
    return blocks;
  }

  function canReceiveNightTransfer(s, receiverId, donorId, start, len) {
    var receiver = s[receiverId] || [];
    var donor = s[donorId] || [];
    if (receiver[start - 2] === "N" || receiver[start - 1 + len] === "N") return false;
    if (nightCooldown(receiver, start - 1)) return false;
    if (nightCooldownAfter(receiver, start - 1, len)) return false;
    for (var i = 0; i < len; i++) {
      var day = start + i;
      if (requestShiftFor(receiverId, day) && requestShiftFor(receiverId, day) !== "N") return false;
      if (requestShiftFor(donorId, day) === "N") return false;
      if (receiver[day - 1] === "N" || donor[day - 1] !== "N") return false;
      if (avoidPairConflictForReceiver(s, receiverId, donorId, day)) return false;
    }
    for (var j = len; j < len + 2 && start - 1 + j < daysInMonth(); j++) {
      var offDay = start + j;
      if (requestShiftFor(receiverId, offDay) && requestShiftFor(receiverId, offDay) !== "OFF") return false;
    }
    var old = [];
    for (var k = 0; k < len; k++) {
      old.push(receiver[start - 1 + k]);
      receiver[start - 1 + k] = "N";
    }
    var ok = maxWork(receiver) <= 4;
    for (var z = 0; z < len; z++) receiver[start - 1 + z] = old[z];
    return ok;
  }

  function avoidPairConflictForReceiver(s, receiverId, donorId, day) {
    return false;
  }

  function avoidPairSoftConflictForReceiver(s, receiverId, donorId, day) {
    var receiver = nurse(receiverId);
    if (!receiver) return false;
    return AVOID_PAIRS.some(function (pair) {
      if (pair.indexOf(receiver.name) < 0) return false;
      var otherName = pair[0] === receiver.name ? pair[1] : pair[0];
      var other = workers().find(function (n) { return n.name === otherName; });
      if (!other || other.id === donorId) return false;
      return isWorkValue((s[other.id] || [])[day - 1]);
    });
  }

  function applyNightTransfer(s, move) {
    for (var i = 0; i < move.len; i++) {
      var idx = move.start - 1 + i;
      var receiverOld = s[move.receiverId][idx];
      s[move.receiverId][idx] = "N";
      s[move.donorId][idx] = receiverOld && receiverOld !== "N" ? receiverOld : "OFF";
    }
    for (var j = move.len; j < move.len + 2 && move.start - 1 + j < daysInMonth(); j++) {
      var offIdx = move.start - 1 + j;
      if (!hasRequest(move.receiverId, offIdx + 1) || requestShiftFor(move.receiverId, offIdx + 1) === "OFF") {
        s[move.receiverId][offIdx] = "OFF";
      }
    }
  }

  function validate(s) {
    var out = [];
    range(daysInMonth()).forEach(function (d) {
      if (requestCount(d) > MAX_DAILY_REQUESTS) out.push({ type: "error", text: d + "\uc77c \uadfc\ubb34 \uc2e0\uccad\uc774 3\uba85\uc744 \ucd08\uacfc\ud588\uc2b5\ub2c8\ub2e4. \ud558\ub8e8\uc5d0 4\uba85 \uc774\uc0c1\uc740 \uc2e0\uccad\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4." });
      WORK_ROLES.forEach(function (role) {
        var same = state.requests.filter(function (r) { var n = nurse(r.nurseId); return r.day === d && n && n.role === role; }).length;
        if (same >= 2) out.push({ type: "warn", text: d + "\uc77c " + ROLE_LABEL[role] + " \ud76c\ub9dd OFF\uac00 " + same + "\uba85 \uacb9\uce69\ub2c8\ub2e4." });
      });
      ["D", "E", "N"].forEach(function (shift) {
        var c = countDay(s, d, shift);
        if (Object.keys(s).length && c < need(shift)) out.push({ type: "error", text: d + "\uc77c " + shift + " \uc778\uc6d0 " + c + "\uba85\uc785\ub2c8\ub2e4. \ucd5c\uc18c " + need(shift) + "\uba85\uc774 \ud544\uc694\ud569\ub2c8\ub2e4." });
        if (Object.keys(s).length && c > maxNeed(shift)) out.push({ type: "error", text: d + "\uc77c " + shift + " \uc778\uc6d0 " + c + "\uba85\uc785\ub2c8\ub2e4. \ucd5c\ub300 " + maxNeed(shift) + "\uba85\uc744 \ub118\uc5c8\uc2b5\ub2c8\ub2e4." });
        var rc = roleCounts(s, d, shift);
        if (c > 0 && (rc.charge < 1 || rc.charge > 1)) out.push({ type: "warn", text: d + "\uc77c " + shift + " \ucc28\uc9c0\uac04\ud638\uc0ac\ub294 \uac00\ub2a5\ud558\uba74 1\uba85\ub9cc \ubc30\uc815\ud558\ub294 \uac83\uc744 \uad8c\uc7a5\ud569\ub2c8\ub2e4. \ud604\uc7ac " + rc.charge + "\uba85\uc785\ub2c8\ub2e4." });
        if (c > 0 && (rc.mid < 2 || rc.mid > 3)) out.push({ type: "warn", text: d + "\uc77c " + shift + " \uc911\uac04\uc5f0\ucc28\ub294 \uad8c\uc7a5 2~3\uba85\uc785\ub2c8\ub2e4. \ud604\uc7ac " + rc.mid + "\uba85\uc785\ub2c8\ub2e4." });
        if (rc.newn > 4) out.push({ type: "warn", text: d + "\uc77c " + shift + " \uc2e0\uaddc\uac04\ud638\uc0ac\uac00 " + rc.newn + "\uba85\uc785\ub2c8\ub2e4." });
      });
    });
    workers().forEach(function (n) {
      var arr = s[n.id] || [];
      var offCnt = countNurse(s, n.id, "OFF");
      if (Object.keys(s).length && offCnt > maxOffAllowed()) {
        out.push({ type: "error", text: n.name + ": OFF " + offCnt + "\uac1c\uc785\ub2c8\ub2e4. \uc81c\uacf5\ud574\uc57c \ud560 \uc624\ud504 " + maxOffAllowed() + "\uac1c\ub97c \ucd08\uacfc\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4." });
      } else if (Object.keys(s).length && offCnt < minOffAllowed()) {
        out.push({ type: "warn", text: n.name + ": OFF " + offCnt + "\uac1c\uc785\ub2c8\ub2e4. \uae30\uc900 OFF " + minOffAllowed() + "\uac1c\ubcf4\ub2e4 \uc801\uc2b5\ub2c8\ub2e4." });
      } else if (Object.keys(s).length && offCnt !== offQuota()) {
        out.push({ type: "warn", text: n.name + ": OFF " + offCnt + "\uac1c, T " + annualLeaveCount(s, n.id) + "\uac1c\uc785\ub2c8\ub2e4. \uc81c\uacf5\ud574\uc57c \ud560 \uc624\ud504\ub294 " + offQuota() + "\uac1c\uc785\ub2c8\ub2e4." });
      }
      var nightCnt = countNurse(s, n.id, "N");
      if (Object.keys(s).length && (nightCnt < 5 || nightCnt > 7)) {
        out.push({ type: "error", text: n.name + ": N " + nightCnt + "\uac1c\uc785\ub2c8\ub2e4. Night\ub294 \ud55c \ub2ec\uc5d0 \ucd5c\uc18c 5\uac1c, \ucd5c\ub300 7\uac1c\uae4c\uc9c0\ub9cc \ud5c8\uc6a9\ub429\ub2c8\ub2e4." });
      }
      var dCnt = countNurse(s, n.id, "D");
      var eCnt = countNurse(s, n.id, "E");
      if (Object.keys(s).length && Math.abs(dCnt - eCnt) >= 6) {
        out.push({ type: "error", text: n.name + ": D " + dCnt + "\uac1c, E " + eCnt + "\uac1c\uc785\ub2c8\ub2e4. Day/Evening \ubd84\ubc30\uac00 \ud55c\ucabd\uc73c\ub85c \ubab0\ub9ac면 안 됩니다." });
      } else if (Object.keys(s).length && Math.abs(dCnt - eCnt) >= 4) {
        out.push({ type: "warn", text: n.name + ": D " + dCnt + "\uac1c, E " + eCnt + "\uac1c\uc785\ub2c8\ub2e4. Day/Evening \ubd84\ubc30를 한 번 더 확인하세요." });
      }
      state.requests.filter(function (r) { return r.nurseId === n.id; }).forEach(function (r) {
        if (Object.keys(s).length && arr[r.day - 1] !== reqShift(r)) out.push({ type: "error", text: n.name + ": " + r.day + "\uc77c \ud76c\ub9dd " + reqShift(r) + "\uac00 \ubc18\uc601\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4." });
      });
      for (var d = 1; d < daysInMonth(); d++) if (arr[d - 1] === "E" && arr[d] === "D") out.push({ type: "error", text: n.name + ": " + d + "\uc77c E \ud6c4 " + (d + 1) + "\uc77c D\uac00 \ubc30\uc815\ub418\uc5c8\uc2b5\ub2c8\ub2e4." });
      for (var i = 0; i < daysInMonth(); i++) {
        if (arr[i] !== "N" || arr[i - 1] === "N") continue;
        var len = 0; while (arr[i + len] === "N") len++;
        var totalLen = i === 0 ? previousEndingNightRunLength(n.id) + len : len;
        if (totalLen === 3 && n.name !== "\uc774\ud61c\ubbf8") out.push({ type: "warn", text: n.name + ": " + (i + 1) + "\uc77c \uc2dc\uc791 N 3\uac1c \uc5f0\uc18d\uc785\ub2c8\ub2e4. \uac00\ub2a5\ud558\uba74 N 2\uac1c \uc5f0\uc18d\uc744 \uad8c\uc7a5\ud569\ub2c8\ub2e4." });
        if (!nightBlockLengthOk(n.id, totalLen)) out.push({ type: "error", text: n.name + ": " + (i + 1) + "\uc77c \uc2dc\uc791 N\uc774 " + totalLen + "\uac1c \uc5f0\uc18d\uc785\ub2c8\ub2e4." });
        if (totalLen < 2 || totalLen > 3) out.push({ type: "error", text: n.name + ": " + (i + 1) + "\uc77c \uc2dc\uc791 N\uc774 " + totalLen + "\uac1c \uc5f0\uc18d\uc785\ub2c8\ub2e4." });
        if (i + len + 1 < daysInMonth() && (arr[i + len] !== "OFF" || arr[i + len + 1] !== "OFF")) out.push({ type: "error", text: n.name + ": N \ud6c4 OFF\uac00 2\uc77c \ubbf8\ub9cc\uc785\ub2c8\ub2e4." });
        for (var cool = len + 2; cool < len + 5 && i + cool < daysInMonth(); cool++) {
          if (arr[i + cool] === "N") out.push({ type: "error", text: n.name + ": N \uc885\ub8cc \ud6c4 5\uc77c \uc774\ub0b4\uc5d0 N\uc774 \ub2e4\uc2dc \ubc30\uc815\ub418\uc5c8\uc2b5\ub2c8\ub2e4." });
        }
      }
      if (maxWork(arr) > 4) out.push({ type: "error", text: n.name + ": \uc5f0\uc18d \uadfc\ubb34\uac00 " + maxWork(arr) + "\uc77c\uc785\ub2c8\ub2e4. 4\uc77c \ucd08\uacfc \uc5f0\uc18d\uadfc\ubb34\ub294 \uae08\uc9c0\uc785\ub2c8\ub2e4." });
      if (eveningOffDayCount(arr) > 0) out.push({ type: "warn", text: n.name + ": E-OFF-D 패턴이 " + eveningOffDayCount(arr) + "번 있습니다. 가능하면 피하도록 조정하세요." });
      if (offTripleBlocks(arr) > 1) out.push({ type: "warn", text: n.name + ": 3\uc77c \uc774\uc0c1 \uc5f0\uc18d OFF\uac00 " + offTripleBlocks(arr) + "\ubc88\uc785\ub2c8\ub2e4. \uc6ec\ub9cc\ud574\uc11c\ub294 \ud55c \ub2ec 1\ubc88\ub9cc \uad8c\uc7a5\ud569\ub2c8\ub2e4." });
    });
    return out;
  }

  function scoreSchedule(s) {
    var score = 10000;
    score -= mandatoryViolationCount(s) * 1000000;
    score -= avoidPairOverlapCount(s) * 10;
    score -= chargeOverlapCount(s) * 2500;
    validate(s).forEach(function (m) { score -= m.type === "error" ? 900 : 45; });
    var ns = workers().map(function (n) { return countNurse(s, n.id, "N"); });
    score -= variance(ns) * 30;
    workers().forEach(function (n) {
      score -= singleWorkBlocks(s[n.id]) * 180;
      score -= Math.max(0, maxWork(s[n.id]) - 4) * 20000;
      score -= Math.abs(countNurse(s, n.id, "N") - 6) * 120;
      score -= Math.max(0, 5 - countNurse(s, n.id, "N")) * 50000;
      score -= Math.max(0, countNurse(s, n.id, "N") - 7) * 50000;
      score -= softBalancePenalty(s, n.id);
      score -= Math.pow(Math.abs(countNurse(s, n.id, "D") - countNurse(s, n.id, "E")), 2) * 220;
      score -= Math.max(0, Math.abs(countNurse(s, n.id, "D") - countNurse(s, n.id, "E")) - 5) * 40000;
      score -= eveningOffDayCount(s[n.id]) * 500;
      score -= Math.max(0, minOffAllowed() - countNurse(s, n.id, "OFF")) * 40;
      score -= Math.max(0, countNurse(s, n.id, "OFF") - maxOffAllowed()) * 50000;
      state.requests.filter(function (r) { return r.nurseId === n.id; }).forEach(function (r) { if ((s[n.id] || [])[r.day - 1] !== reqShift(r)) score -= 35; });
      score -= Math.max(0, offTripleBlocks(s[n.id]) - 1) * 60;
    });
    return score;
  }

  function avoidPairOverlapCount(s) {
    var count = 0;
    range(daysInMonth()).forEach(function (d) {
      AVOID_PAIRS.forEach(function (pair) {
        var a = workers().find(function (n) { return n.name === pair[0]; });
        var b = workers().find(function (n) { return n.name === pair[1]; });
        if (a && b && isWorkValue(((s || {})[a.id] || [])[d - 1]) && isWorkValue(((s || {})[b.id] || [])[d - 1])) count++;
      });
    });
    return count;
  }

  function chargeOverlapCount(s) {
    var count = 0;
    range(daysInMonth()).forEach(function (d) {
      ["D", "E", "N"].forEach(function (shift) {
        count += Math.max(0, countRoleDay(s, d, shift, "charge") - 1);
      });
    });
    return count;
  }

  function exportExcel() { downloadTable("xls"); }
  function exportDoc() { downloadTable("doc"); }
  function downloadTable(kind) {
    if (!Object.keys(state.schedule || {}).length) return;
    var html = '<html><head><meta charset="utf-8"></head><body>' + tableHtml() + '</body></html>';
    var blob = new Blob(["\ufeff" + html], { type: "application/vnd.ms-excel;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "\uac04\ud638\uc0ac_\uadfc\ubb34\ud45c_" + state.year + "_" + pad(state.month) + "." + kind;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 800);
  }

  function tableHtml() {
    var totalCols = daysInMonth() + 7;
    var score = scoreSchedule(state.schedule || {});
    var mandatory = mandatoryViolationCount(state.schedule || {});
    var h = '<table border="1"><tr><th colspan="' + totalCols + '">\uadfc\ubb34\ud45c \uc810\uc218: ' + Math.round(score) + '\uc810</th></tr>' +
      '<tr><td colspan="' + totalCols + '">1\uc21c\uc704/2\uc21c\uc704 \uc704\ubc18 ' + mandatory + '\uac1c, \uc624\ub958 ' + validationCount(state.schedule, "error") + '\uac1c, \uacbd\uace0 ' + validationCount(state.schedule, "warn") + '\uac1c</td></tr>' +
      '<tr><th>\uc774\ub984</th><th>\uc720\ud615</th>' + range(daysInMonth()).map(function (d) { return '<th' + exportDayStyle(d, false) + '>' + d + '\uc77c</th>'; }).join("") + '<th>D \ud69f\uc218</th><th>E \ud69f\uc218</th><th>N \ud69f\uc218</th><th>off</th><th>T</th></tr>';
    var lastRole = "";
    scheduleNurses().forEach(function (n) {
      if (lastRole && lastRole !== n.role && (n.role === "mid" || n.role === "newn")) {
        h += '<tr><td colspan="' + (daysInMonth() + 7) + '">&nbsp;</td></tr>';
      }
      h += '<tr><td>' + esc(n.name) + '</td><td>' + ROLE_LABEL[n.role] + '</td>' + range(daysInMonth()).map(function (d) { var v = (state.schedule[n.id] || [])[d - 1] || ""; return '<td' + exportCellStyle(n, d, v) + '>' + v + '</td>'; }).join("") + '<td' + exportSummaryStyle(n, "D") + '>' + countNurse(state.schedule, n.id, "D") + '</td><td' + exportSummaryStyle(n, "E") + '>' + countNurse(state.schedule, n.id, "E") + '</td><td' + exportSummaryStyle(n, "N") + '>' + countNurse(state.schedule, n.id, "N") + '</td><td' + exportSummaryStyle(n, "OFF") + '>' + countNurse(state.schedule, n.id, "OFF") + '</td><td>' + annualLeaveCount(state.schedule, n.id) + '</td></tr>';
      lastRole = n.role;
    });
    ["D", "E", "N"].forEach(function (shift) {
      h += '<tr><td colspan="2">' + shift + ' \uc778\uc6d0</td>' + range(daysInMonth()).map(function (d) { return '<td' + exportDailyCountStyle(d, shift) + '>' + countDay(state.schedule, d, shift) + '</td>'; }).join("") + '<td></td><td></td><td></td><td></td><td></td></tr>';
    });
    return h + '</table>';
  }

  function exportDayStyle(day, requested) {
    if (requested) return ' style="background:#fff176;font-weight:bold"';
    if (isWeekend(day) || isHoliday(day)) return ' style="background:#fde2e8"';
    return "";
  }

  function exportRedStyle() {
    return ' style="background:#fca5a5;color:#111827;font-weight:bold"';
  }

  function exportCellStyle(n, day, value) {
    var arr = state.schedule[n.id] || [];
    var bad = false;
    if (hasRequest(n.id, day) && value !== requestShiftFor(n.id, day)) bad = true;
    if (value === "D" && arr[day - 2] === "E") bad = true;
    if (value === "E" && arr[day] === "D") bad = true;
    if (invalidNightCell(n.id, arr, day)) bad = true;
    if (longWorkCell(arr, day)) bad = true;
    if (value === "OFF" && countNurse(state.schedule, n.id, "OFF") > maxOffAllowed()) bad = true;
    return bad ? exportRedStyle() : exportDayStyle(day, hasRequest(n.id, day));
  }

  function exportSummaryStyle(n, kind) {
    var dCnt = countNurse(state.schedule, n.id, "D");
    var eCnt = countNurse(state.schedule, n.id, "E");
    var nCnt = countNurse(state.schedule, n.id, "N");
    var offCnt = countNurse(state.schedule, n.id, "OFF");
    if ((kind === "D" || kind === "E") && Math.abs(dCnt - eCnt) >= 6) return exportRedStyle();
    if (kind === "N" && (nCnt < 5 || nCnt > 7)) return exportRedStyle();
    if (kind === "OFF" && offCnt > maxOffAllowed()) return exportRedStyle();
    return "";
  }

  function exportDailyCountStyle(day, shift) {
    var c = countDay(state.schedule, day, shift);
    return (c < need(shift) || c > maxNeed(shift)) ? exportRedStyle() : exportDayStyle(day, false);
  }

  function invalidNightCell(id, arr, day) {
    var idx = day - 1;
    if ((arr || [])[idx] !== "N") return false;
    var start = idx;
    while (start > 0 && arr[start - 1] === "N") start--;
    var end = idx;
    while (end + 1 < daysInMonth() && arr[end + 1] === "N") end++;
    var len = end - start + 1;
    var totalLen = start === 0 ? previousEndingNightRunLength(id) + len : len;
    if (!nightBlockLengthOk(id, totalLen) || totalLen < 2 || totalLen > 3) return true;
    if (end + 2 < daysInMonth() && (arr[end + 1] !== "OFF" || arr[end + 2] !== "OFF")) return true;
    return false;
  }

  function longWorkCell(arr, day) {
    if (!isWorkValue((arr || [])[day - 1])) return false;
    var count = 0;
    for (var i = day - 1; i >= 0 && isWorkValue(arr[i]); i--) count++;
    for (var j = day; j < daysInMonth() && isWorkValue(arr[j]); j++) count++;
    return count > 4;
  }

  function nursesForLogin() { return state.nurses.filter(function (n) { return n.role !== "head" && n.role !== "edu"; }); }
  function scheduleNurses() { return state.nurses.filter(function (n) { return n.role !== "head" && n.role !== "edu"; }); }
  function workers() { return state.nurses.filter(function (n) { return WORK_ROLES.indexOf(n.role) >= 0; }); }
  function hasFinalSchedule() { return !!(state.finalSchedule && Object.keys(state.finalSchedule).some(function (id) { return (state.finalSchedule[id] || []).some(Boolean); })); }
  function hasPreviousSchedule() { return !!(state.previousSchedule && Object.keys(state.previousSchedule).some(function (id) { return (state.previousSchedule[id] || []).some(Boolean); })); }
  function nightRangeOk(s) {
    return workers().every(function (n) {
      var count = countNurse(s, n.id, "N");
      return count >= 5 && count <= 7;
    });
  }

  function nightTargetCounts(s) {
    var ns = workers();
    var totalNeeded = need("N") * daysInMonth();
    var minTotal = ns.length * 5;
    var maxTotal = ns.length * 7;
    var targetTotal = Math.min(maxTotal, Math.max(minTotal, totalNeeded));
    var targets = {};
    ns.forEach(function (n) {
      targets[n.id] = clamp(countNurse(s, n.id, "N"), 5, 7);
    });
    var current = ns.reduce(function (sum, n) { return sum + targets[n.id]; }, 0);
    var ordered = shuffle(ns).sort(function (a, b) {
      return countNurse(s, a.id, "N") - countNurse(s, b.id, "N") || workCount(s, a.id) - workCount(s, b.id);
    });
    while (current < targetTotal) {
      var up = ordered.find(function (n) { return targets[n.id] < 7; });
      if (!up) break;
      targets[up.id]++;
      current++;
      ordered.push(ordered.shift());
    }
    while (current > targetTotal) {
      var down = ordered.slice().reverse().find(function (n) { return targets[n.id] > Math.max(5, countNurse(s, n.id, "N")); });
      if (!down) break;
      targets[down.id]--;
      current--;
    }
    return targets;
  }

  function hardImpossibleReason() {
    var ns = workers();
    if (!ns.length) return "";
    var totalNeeded = need("N") * daysInMonth();
    if (totalNeeded > ns.length * 7) {
      return "현재 나이트 필요 인원이 많아서 모든 간호사 N 5~7개 조건을 만족할 수 없습니다.";
    }
    if (totalNeeded < ns.length * 5) {
      return "현재 나이트 필요 인원이 적어서 모든 간호사 N 5~7개 조건을 만족할 수 없습니다.";
    }
    return "";
  }

  function hardScheduleOk(s) {
    return Object.keys(s || {}).length > 0 && validate(s).every(function (m) { return m.type !== "error"; });
  }

  function mandatoryScheduleOk(s) {
    return Object.keys(s || {}).length > 0 && mandatoryViolationCount(s) === 0;
  }

  function mandatoryViolationCount(s) {
    var count = 0;
    range(daysInMonth()).forEach(function (d) {
      var nStaff = countDay(s, d, "N");
      if (nStaff < NIGHT_MIN) count += NIGHT_MIN - nStaff;
      if (nStaff > NIGHT_MAX) count += nStaff - NIGHT_MAX;
    });
    workers().forEach(function (n) {
      var arr = (s || {})[n.id] || [];
      var nCnt = countNurse(s, n.id, "N");
      if (nCnt < 5) count += 5 - nCnt;
      if (nCnt > 7) count += nCnt - 7;
      for (var d = 1; d < daysInMonth(); d++) {
        if (arr[d - 1] === "E" && arr[d] === "D") count++;
      }
      for (var i = 0; i < daysInMonth(); i++) {
        if (arr[i] !== "N" || arr[i - 1] === "N") continue;
        var len = 0;
        while (arr[i + len] === "N") len++;
        var totalLen = i === 0 ? previousEndingNightRunLength(n.id) + len : len;
        if (!nightBlockLengthOk(n.id, totalLen)) count++;
        if (totalLen < 2 || totalLen > 3) count++;
        if (i + len < daysInMonth() && arr[i + len] !== "OFF") count++;
        if (i + len + 1 < daysInMonth() && arr[i + len + 1] !== "OFF") count++;
      }
    });
    return count;
  }

  function softBalancePenalty(s, id) {
    var dCnt = countNurse(s, id, "D");
    var eCnt = countNurse(s, id, "E");
    var deTotal = dCnt + eCnt;
    if (deTotal < 6) return Math.pow(Math.abs(dCnt - eCnt), 2) * 300;
    return Math.max(0, 3 - dCnt) * 25000 + Math.max(0, 3 - eCnt) * 25000 + Math.pow(Math.abs(dCnt - eCnt), 2) * 500;
  }

  function preferredNightBlockLen(id) {
    var n = nurse(id);
    return n && n.name === "\uc774\ud61c\ubbf8" ? 3 : 2;
  }

  function nightBlockLengthOk(id, len) {
    var n = nurse(id);
    if (n && n.name === "\uc774\ud61c\ubbf8") return len === 3;
    return len >= 2 && len <= 3;
  }

  function dayEveningBalanceOk(s, id) {
    return Math.abs(countNurse(s, id, "D") - countNurse(s, id, "E")) < 6;
  }

  function shiftBalanceScore(s, id, shift) {
    var dCnt = countNurse(s, id, "D");
    var eCnt = countNurse(s, id, "E");
    return shift === "D" ? dCnt - eCnt : eCnt - dCnt;
  }

  function eveningOffDayCount(arr) {
    var count = 0;
    for (var i = 0; i < daysInMonth() - 2; i++) {
      if ((arr || [])[i] === "E" && (arr || [])[i + 1] === "OFF" && (arr || [])[i + 2] === "D") count++;
    }
    return count;
  }

  function bedsForNurse(dateKey, shift, nurseId) {
    var source = (((state.bedAssignments || {})[dateKey] || {})[shift] || {})[nurseId];
    if (source === ACTING_VALUE) return [];
    return Array.isArray(source) ? source.filter(function (n) { return n >= 1 && n <= 26; }) : [];
  }
  function isActingAssignment(dateKey, shift, nurseId) {
    return (((state.bedAssignments || {})[dateKey] || {})[shift] || {})[nurseId] === ACTING_VALUE;
  }
  function bedAssignDateParts() {
    var day = clamp(Number(el.nfBedAssignDay && el.nfBedAssignDay.value), 1, daysInMonth());
    return {
      year: state.year,
      month: state.month,
      day: day,
      weekday: new Date(state.year, state.month - 1, day).getDay()
    };
  }
  function insertAtCursor(input, text) {
    if (!input) return;
    input.focus();
    var start = input.selectionStart == null ? input.value.length : input.selectionStart;
    var end = input.selectionEnd == null ? input.value.length : input.selectionEnd;
    input.value = input.value.slice(0, start) + text + input.value.slice(end);
    var next = start + text.length;
    if (input.setSelectionRange) input.setSelectionRange(next, next);
  }
  function parseBeds(value) {
    var out = [];
    String(value || "").split(/[,\s.]+/).forEach(function (part) {
      if (!part) return;
      var rangeMatch = part.match(/^(\d{1,2})-(\d{1,2})$/);
      if (rangeMatch) {
        var a = Number(rangeMatch[1]), b = Number(rangeMatch[2]);
        for (var i = Math.min(a, b); i <= Math.max(a, b); i++) if (i >= 1 && i <= 26) out.push(i);
      } else {
        var n = Number(part);
        if (n >= 1 && n <= 26) out.push(n);
      }
    });
    return uniq(out).sort(function (a, b) { return a - b; });
  }
  function todayKey(parts) { return parts.year + "-" + pad(parts.month) + "-" + pad(parts.day); }
  function setToKoreaToday() {
    var today = koreaTodayParts();
    if (state.year !== today.year || state.month !== today.month) { clearFinalStateOnly(); clearPreviousStateOnly(); }
    state.year = today.year;
    state.month = today.month;
    state.todayDay = today.day;
    save();
  }
  function selectedTodayParts() {
    var day = clamp(Number(state.todayDay || (el.nfTodayDay && el.nfTodayDay.value)), 1, daysInMonth());
    return {
      year: state.year,
      month: state.month,
      day: day,
      weekday: new Date(state.year, state.month - 1, day).getDay()
    };
  }
  function koreaTodayParts() {
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Seoul",
      year: "numeric",
      month: "numeric",
      day: "numeric",
      weekday: "short"
    }).formatToParts(new Date());
    var out = {};
    parts.forEach(function (p) { out[p.type] = p.value; });
    var weekdayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
    return {
      year: Number(out.year),
      month: Number(out.month),
      day: Number(out.day),
      weekday: weekdayMap[out.weekday] == null ? new Date().getDay() : weekdayMap[out.weekday]
    };
  }
  function autoTries() { return Math.min(300, Math.max(120, workers().length * 5)); }
  function need(shift) { return shift === "N" ? NIGHT_MIN : Math.max(7, Number(state.needs[shift]) || 0); }
  function maxNeed(shift) { return shift === "N" ? NIGHT_MAX : Math.max(need(shift), Number((state.maxNeeds || {})[shift]) || need(shift)); }
  function nurse(id) { return state.nurses.find(function (n) { return n.id === id; }); }
  function hasRequest(id, day) { return state.requests.some(function (r) { return r.nurseId === id && r.day === day; }); }
  function requestShiftFor(id, day) { var r = state.requests.find(function (x) { return x.nurseId === id && x.day === day; }); return r ? reqShift(r) : ""; }
  function requestCount(day) { return state.requests.filter(function (r) { return r.day === day; }).length; }
  function requestCountExcluding(nurseId, day) { return state.requests.filter(function (r) { return r.day === day && r.nurseId !== nurseId; }).length; }
  function daysInMonth() { return new Date(state.year, state.month, 0).getDate(); }
  function dow(day) { return DOW[new Date(state.year, state.month - 1, day).getDay()]; }
  function isWeekend(day) { var x = new Date(state.year, state.month - 1, day).getDay(); return x === 0 || x === 6; }
  function isHoliday(day) { return state.holidays.indexOf(day) >= 0; }
  function offQuota() { return maxOffAllowed(); }
  function maxOffAllowed() { return Math.max(baseOff(), Number(state.maxOffTotal) || baseOff()); }
  function minOffAllowed() { return baseOff(); }
  function baseOff() { return Math.max(0, Number(state.baseOff) || 0); }
  function annualLeaveCount(s, id) { return Math.max(0, countNurse(s, id, "OFF") - baseOff()); }
  function parseDays(v) { return uniq(String(v || "").split(/[,\s]+/).map(Number).filter(function (n) { return n >= 1 && n <= daysInMonth(); })).sort(function (a, b) { return a - b; }); }
  function dayClass(d) { return isHoliday(d) ? "holiday" : (isWeekend(d) ? "weekend" : ""); }
  function personalShiftLabel(shift) { return ({ D: "\ub370\uc774", E: "\uc774\ube0c\ub2dd", N: "\ub098\uc774\ud2b8", OFF: "\uc624\ud504", MD: "MD" })[shift] || ""; }
  function personalShiftClass(shift) { return shift ? "ps-" + shift : "ps-empty"; }
  function countDay(s, day, shift) { return workers().filter(function (n) { return (s[n.id] || [])[day - 1] === shift; }).length; }
  function countRoleDay(s, day, shift, role) { return workers().filter(function (n) { return n.role === role && (s[n.id] || [])[day - 1] === shift; }).length; }
  function countNurse(s, id, shift) { return (s[id] || []).filter(function (v) { return v === shift; }).length; }
  function workCount(s, id) { return (s[id] || []).filter(function (v) { return v === "D" || v === "E" || v === "N"; }).length; }
  function roleCounts(s, day, shift) { var out = { charge: 0, mid: 0, newn: 0 }; workers().forEach(function (n) { if ((s[n.id] || [])[day - 1] === shift) out[n.role]++; }); return out; }
  function validationCount(s, type) { return validate(s).filter(function (m) { return m.type === type; }).length; }
  function cloneSchedule(s) {
    var out = {};
    Object.keys(s || {}).forEach(function (id) { out[id] = (s[id] || []).slice(); });
    return out;
  }
  function schedulesEqual(a, b) { return JSON.stringify(a || {}) === JSON.stringify(b || {}); }
  function sleep(ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); }
  function maxWork(arr) { var m = 0, c = 0; (arr || []).forEach(function (v) { if (v && v !== "OFF") { c++; if (c > m) m = c; } else c = 0; }); return m; }
  function singleWorkBlocks(arr) { var blocks = 0, c = 0; (arr || []).forEach(function (v) { if (v && v !== "OFF") c++; else { if (c === 1) blocks++; c = 0; } }); if (c === 1) blocks++; return blocks; }
  function offTripleBlocks(arr) { var blocks = 0, c = 0; (arr || []).forEach(function (v) { if (v === "OFF") c++; else { if (c >= 3) blocks++; c = 0; } }); if (c >= 3) blocks++; return blocks; }
  function variance(a) { if (!a.length) return 0; var avg = a.reduce(function (x, y) { return x + y; }, 0) / a.length; return a.reduce(function (s, v) { return s + Math.pow(v - avg, 2); }, 0) / a.length; }
  function range(n) { return Array.from({ length: n }, function (_, i) { return i + 1; }); }
  function qsa(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function clamp(v, min, max) { return Number.isFinite(v) ? Math.max(min, Math.min(max, v)) : min; }
  function uniq(a) { return a.filter(function (v, i) { return a.indexOf(v) === i; }); }
  function shuffle(a) { var x = a.slice(); for (var i = x.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = x[i]; x[i] = x[j]; x[j] = t; } return x; }
  function msg(type, text) { return '<div class="msg ' + type + '">' + esc(text) + '</div>'; }
  function esc(v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (m) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[m]; }); }
  function pad(n) { return String(n).padStart(2, "0"); }
})();
