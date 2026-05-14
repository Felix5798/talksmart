<script setup>
import { onMounted, ref } from "vue";

const uid = ref("1001");
const conversations = ref([]);
const activeId = ref(null);
const messages = ref([]);
const input = ref("");
const streaming = ref(false);
const liveText = ref("");

const API = "/api";

async function loadConversations() {
  const r = await fetch(`${API}/conversations?uid=${encodeURIComponent(uid.value)}`);
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  conversations.value = data.items || [];
}

async function selectConversation(id) {
  activeId.value = id;
  liveText.value = "";
  const r = await fetch(
    `${API}/conversations/${encodeURIComponent(id)}/messages?uid=${encodeURIComponent(uid.value)}`,
  );
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  messages.value = data.messages || [];
}

async function newChat() {
  activeId.value = null;
  messages.value = [];
  liveText.value = "";
}

async function deleteActive() {
  if (!activeId.value) return;
  const id = activeId.value;
  const r = await fetch(
    `${API}/conversations/${encodeURIComponent(id)}?uid=${encodeURIComponent(uid.value)}`,
    { method: "DELETE" },
  );
  if (!r.ok) throw new Error(await r.text());
  await newChat();
  await loadConversations();
}

function parseSseBlock(block) {
  const lines = block.split("\n");
  for (const line of lines) {
    if (line.startsWith("data:")) {
      const raw = line.slice(5).trim();
      try {
        return JSON.parse(raw);
      } catch {
        return null;
      }
    }
  }
  return null;
}

async function send() {
  const text = input.value.trim();
  if (!text || streaming.value) return;
  input.value = "";
  streaming.value = true;
  liveText.value = "";

  const payload = {
    uid: uid.value,
    conversation_id: activeId.value,
    message: text,
  };

  if (!activeId.value) {
    messages.value = [...messages.value, { role: "user", content: text }];
  } else {
    messages.value = [...messages.value, { role: "user", content: text }];
  }

  const res = await fetch(`${API}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) {
    streaming.value = false;
    messages.value = [
      ...messages.value,
      { role: "assistant", content: `[错误] ${await res.text()}` },
    ];
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const block of parts) {
      const evt = parseSseBlock(block);
      if (!evt) continue;
      if (evt.type === "meta" && evt.conversation_id) {
        activeId.value = evt.conversation_id;
      } else if (evt.type === "token" && evt.text) {
        liveText.value += evt.text;
      } else if (evt.type === "done") {
        // handled after loop
      }
    }
  }

  if (buffer.trim()) {
    const evt = parseSseBlock(buffer);
    if (evt?.type === "token" && evt.text) liveText.value += evt.text;
  }

  liveText.value = "";
  streaming.value = false;

  await loadConversations();
  if (activeId.value) {
    await selectConversation(activeId.value);
  }
}

onMounted(() => {
  loadConversations().catch(console.error);
});
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">电商智能客服</div>
      <div class="uid">
        <label>uid</label>
        <input v-model="uid" />
      </div>
      <button class="btn primary" @click="newChat">新对话</button>
      <button class="btn danger" :disabled="!activeId" @click="deleteActive">删除当前</button>
      <div class="conv-list">
        <button
          v-for="c in conversations"
          :key="c.conversation_id"
          class="conv"
          :class="{ active: c.conversation_id === activeId }"
          @click="selectConversation(c.conversation_id)"
        >
          {{ c.conversation_id.slice(0, 8) }}…
        </button>
      </div>
    </aside>
    <main class="main">
      <div class="messages">
        <div v-for="(m, idx) in messages" :key="idx" class="bubble" :class="m.role">
          {{ m.content }}
        </div>
        <div v-if="liveText" class="bubble assistant">{{ liveText }}</div>
      </div>
      <div class="composer">
        <textarea v-model="input" rows="3" placeholder="输入消息…（试：退货政策 / 我的订单 / 物流 / 转人工）" />
        <button class="btn primary send" :disabled="streaming" @click="send">发送</button>
      </div>
    </main>
  </div>
</template>

<style>
:root {
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "PingFang SC", sans-serif;
  color: #111;
  background: #f4f5f7;
}
body {
  margin: 0;
}
.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: 100vh;
}
.sidebar {
  background: #111827;
  color: #e5e7eb;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.brand {
  font-weight: 700;
  font-size: 16px;
}
.uid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}
.uid input {
  padding: 8px;
  border-radius: 8px;
  border: 1px solid #374151;
  background: #0b1220;
  color: #e5e7eb;
}
.btn {
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 600;
}
.btn.primary {
  background: #2563eb;
  color: #fff;
}
.btn.danger {
  background: #7f1d1d;
  color: #fecaca;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.conv-list {
  overflow: auto;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.conv {
  text-align: left;
  border: 1px solid #374151;
  background: #0b1220;
  color: #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
}
.conv.active {
  border-color: #60a5fa;
}
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.messages {
  flex: 1;
  overflow: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.bubble {
  max-width: 720px;
  padding: 12px 14px;
  border-radius: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.bubble.user {
  align-self: flex-end;
  background: #dbeafe;
}
.bubble.assistant {
  align-self: flex-start;
  background: #fff;
  border: 1px solid #e5e7eb;
}
.composer {
  border-top: 1px solid #e5e7eb;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  background: #fff;
}
textarea {
  width: 100%;
  resize: vertical;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  padding: 10px;
  font: inherit;
}
.send {
  align-self: end;
}
</style>
