<template>
  <div class="admin">
    <div class="section">
      <div class="section-header">
        <div>
          <h2>用户管理</h2>
          <p>管理账号、角色与权限分配。</p>
        </div>
      </div>

      <div class="panel user-panel">
        <div class="user-toolbar">
          <div ref="filterRef" class="search-box filter-box">
            <button class="filter-trigger" type="button" @click="toggleFilter">
              {{ userFilterField === 'username' ? '用户名' : '账号' }}
              <span class="caret" :class="{ open: filterOpen }"></span>
            </button>
            <transition name="slide-fade">
              <div v-if="filterOpen" class="filter-dropdown">
                <button class="filter-option" type="button" @click="selectFilter('username')">
                  用户名
                </button>
                <button class="filter-option" type="button" @click="selectFilter('account')">
                  账号
                </button>
              </div>
            </transition>
            <input
              v-model="userSearch"
              type="text"
              :placeholder="userFilterField === 'username' ? '搜索用户名' : '搜索账号'"
            />
          </div>
          <div class="toolbar-actions">
            <button class="ghost" type="button" @click="handleSyncUsers">同步用户</button>
            <button class="primary" type="button" @click="toggleUserForm">
              {{ showUserForm ? '收起' : '添加用户' }}
            </button>
          </div>
        </div>

        <div v-if="showUserForm" class="user-form-panel">
          <form class="form" @submit.prevent="handleCreateUser">
            <div class="field">
              <label>账号</label>
              <input v-model="userForm.account" type="text" placeholder="demo" required />
            </div>
            <div class="field">
              <label>用户名</label>
              <input v-model="userForm.username" type="text" placeholder="Demo User" required />
            </div>
            <div class="field">
              <label>邮箱</label>
              <input v-model="userForm.email" type="email" placeholder="user@example.com" required />
            </div>
            <div class="field">
              <label>密码</label>
              <input v-model="userForm.password" type="password" placeholder="至少 6 位" required />
            </div>
            <div class="field">
              <label>角色</label>
              <select v-model="userForm.role">
                <option v-if="!roles.length" value="user">user</option>
                <option v-for="role in roles" :key="role.id" :value="role.name">
                  {{ role.name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label>用户状态</label>
              <select v-model="userForm.status">
                <option value="active">active</option>
                <option value="disabled">disabled</option>
              </select>
            </div>
            <div class="field">
              <label>用户来源</label>
              <input v-model="userForm.source" type="text" placeholder="local" />
            </div>
            <div class="field">
              <label>工作空间</label>
              <input v-model="userForm.workspace" type="text" placeholder="default" />
            </div>
            <div class="button-row">
              <button class="primary" type="submit" :disabled="userLoading">
                {{ userLoading ? '创建中...' : '创建用户' }}
              </button>
            </div>
          </form>
        </div>

        <p v-if="userError" class="state error">{{ userError }}</p>
        <p v-if="userSuccess" class="state success">{{ userSuccess }}</p>

        <div class="table">
          <div class="table-head">
            <div class="col col-check"><input type="checkbox" disabled /></div>
            <div class="col col-name">用户名</div>
            <div class="col col-account">账号</div>
            <div class="col col-status">用户状态</div>
            <div class="col col-email">邮箱</div>
            <div class="col col-source">用户来源</div>
            <div class="col col-workspace">工作空间</div>
            <div class="col col-created">创建时间</div>
            <div class="col col-actions">角色</div>
          </div>

          <div v-if="usersLoading" class="state">加载用户中...</div>
          <div v-else-if="usersError" class="state error">{{ usersError }}</div>

          <div v-else-if="filteredUsers.length" class="table-body">
            <div v-for="user in filteredUsers" :key="user.id" class="table-row">
              <div class="col col-check"><input type="checkbox" /></div>
              <div class="col col-name">{{ user.username }}</div>
              <div class="col col-account">{{ user.account }}</div>
              <div class="col col-status">
                <div class="inline-dropdown" @click.stop>
                  <button
                    class="filter-trigger inline-trigger"
                    type="button"
                    :disabled="user.account === 'admin'"
                    @click.stop="toggleStatusDropdown(user.id)"
                  >
                    <span>{{ user.status }}</span>
                    <span class="caret" :class="{ open: statusOpenFor === user.id }"></span>
                  </button>
                  <div
                    v-if="statusOpenFor === user.id"
                    class="filter-dropdown inline-dropdown-panel"
                  >
                    <button
                      class="filter-option"
                      type="button"
                      @click="setUserStatus(user, 'active')"
                    >
                      active
                    </button>
                    <button
                      class="filter-option"
                      type="button"
                      @click="setUserStatus(user, 'disabled')"
                    >
                      disabled
                    </button>
                  </div>
                </div>
              </div>
              <div class="col col-email">{{ user.email }}</div>
              <div class="col col-source">{{ user.source || 'local' }}</div>
              <div class="col col-workspace">{{ user.workspace || 'default' }}</div>
              <div class="col col-created">
                {{ new Date(user.created_at).toLocaleString() }}
              </div>
              <div class="col col-actions">
                <div class="inline-dropdown" @click.stop>
                  <button
                    class="filter-trigger inline-trigger"
                    type="button"
                    :disabled="user.account === 'admin'"
                    @click.stop="toggleRoleDropdown(user.id)"
                  >
                    <span>{{ user.role }}</span>
                    <span class="caret" :class="{ open: roleOpenFor === user.id }"></span>
                  </button>
                  <div
                    v-if="roleOpenFor === user.id"
                    class="filter-dropdown inline-dropdown-panel"
                  >
                    <button
                      v-for="role in roles"
                      :key="role.id"
                      class="filter-option"
                      type="button"
                      @click="setUserRole(user, role.name)"
                    >
                      {{ role.name }}
                    </button>
                    <button
                      v-if="!roles.length"
                      class="filter-option"
                      type="button"
                      @click="setUserRole(user, 'user')"
                    >
                      user
                    </button>
                  </div>
                </div>
                <button
                  class="ghost action-control"
                  type="button"
                  :disabled="user.account === 'admin'"
                  :title="user.account === 'admin' ? 'admin 账号不可修改角色/状态' : ''"
                  @click="handleUpdateUser(user)"
                >
                  保存
                </button>
                <button
                  class="ghost danger action-control"
                  type="button"
                  @click="openResetPassword(user)"
                >
                  重置密码
                </button>
                <button
                  class="ghost danger action-control"
                  type="button"
                  :disabled="user.account === 'admin'"
                  :title="user.account === 'admin' ? 'admin 账号不可删除' : ''"
                  @click="openDeleteUser(user)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
          <div v-else class="state">暂无用户数据</div>
        </div>
      </div>
    </div>

    <div v-if="showResetModal" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h3>重置密码</h3>
          <button class="modal-close" type="button" @click="closeResetModal">✕</button>
        </div>
        <p class="modal-body">
          确认将 <strong>{{ resetTarget?.username }}</strong> 的密码重置为
          <code>agentui@2025</code> 吗？
        </p>
        <div class="modal-actions">
          <button class="ghost" type="button" @click="closeResetModal">取消</button>
          <button class="primary" type="button" :disabled="resetting" @click="confirmResetPassword">
            {{ resetting ? '处理中...' : '确认重置' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h3>删除用户</h3>
          <button class="modal-close" type="button" @click="closeDeleteModal">✕</button>
        </div>
        <p class="modal-body">
          确认删除 <strong>{{ deleteTarget?.username }}</strong> 吗？该用户的权限数据将一并删除。
        </p>
        <div class="modal-actions">
          <button class="ghost" type="button" @click="closeDeleteModal">取消</button>
          <button class="primary" type="button" :disabled="deleting" @click="confirmDeleteUser">
            {{ deleting ? '处理中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showRoleDeleteModal" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h3>删除角色</h3>
          <button class="modal-close" type="button" @click="closeRoleDeleteModal">✕</button>
        </div>
        <p class="modal-body">
          确认删除 <strong>{{ roleDeleteTarget?.name }}</strong> 吗？该角色的权限数据将一并删除。
        </p>
        <div class="modal-actions">
          <button class="ghost" type="button" @click="closeRoleDeleteModal">取消</button>
          <button class="primary" type="button" :disabled="roleDeleting" @click="confirmDeleteRole">
            {{ roleDeleting ? '处理中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showGroupDeleteModal" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h3>删除分组</h3>
          <button class="modal-close" type="button" @click="closeGroupDeleteModal">✕</button>
        </div>
        <p class="modal-body">
          确认删除 <strong>{{ groupDeleteTarget?.name }}</strong> 吗？该分组关联的权限数据将一并删除。
        </p>
        <div class="modal-actions">
          <button class="ghost" type="button" @click="closeGroupDeleteModal">取消</button>
          <button
            class="primary"
            type="button"
            :disabled="groupDeleting"
            @click="confirmDeleteGroup"
          >
            {{ groupDeleting ? '处理中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showApiDeleteModal" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h3>删除 API 配置</h3>
          <button class="modal-close" type="button" @click="closeApiDeleteModal">✕</button>
        </div>
        <p class="modal-body">
          确认删除 <strong>{{ apiDeleteTarget?.base_url }}</strong> 吗？
        </p>
        <div class="modal-actions">
          <button class="ghost" type="button" @click="closeApiDeleteModal">取消</button>
          <button
            class="primary"
            type="button"
            :disabled="apiConfigLoading"
            @click="confirmDeleteApiConfig"
          >
            {{ apiConfigLoading ? '处理中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showApiSyncModal" class="modal-backdrop">
      <div class="modal-card modal-large">
        <div class="modal-header">
          <h3>同步智能体</h3>
          <button class="modal-close" type="button" @click="closeApiSyncModal">✕</button>
        </div>
        <div class="modal-body">
          <div class="sync-grid">
            <div class="sync-panel">
              <div class="sync-panel-header">
                <span class="column-title">工作空间</span>
              </div>
              <div v-if="syncWorkspaceLoading" class="state">加载工作空间中...</div>
              <div v-else-if="syncWorkspaceError" class="state error">
                {{ syncWorkspaceError }}
              </div>
              <div v-else class="list">
                <button
                  v-for="workspace in syncWorkspaces"
                  :key="workspace.id"
                  class="list-item"
                  :class="{ active: selectedWorkspaceId === workspace.id }"
                  type="button"
                  @click="selectWorkspace(workspace)"
                >
                  <strong>{{ workspace.name }}</strong>
                  <small>{{ workspace.id }}</small>
                </button>
                <div v-if="!syncWorkspaces.length" class="state">暂无工作空间</div>
              </div>
            </div>
            <div class="sync-panel">
              <div class="sync-panel-header">
                <span class="column-title">智能体</span>
                <label class="checkbox-line">
                  <input
                    type="checkbox"
                    :checked="allAppsSelected"
                    :disabled="!syncApps.length"
                    @change="toggleSelectAllApps"
                  />
                  <span>全选</span>
                </label>
              </div>
              <div v-if="syncAppsLoading" class="state">加载智能体中...</div>
              <div v-else-if="syncAppsError" class="state error">{{ syncAppsError }}</div>
              <div v-else class="list">
                <label
                  v-for="app in syncApps"
                  :key="app.id"
                  class="list-item checkbox-item"
                >
                  <input
                    type="checkbox"
                    :checked="selectedAppIds.includes(app.id)"
                    @change="toggleAppSelection(app.id)"
                  />
                  <div class="checkbox-text">
                    <strong>{{ app.name }}</strong>
                    <small>{{ app.id }}</small>
                  </div>
                </label>
                <div v-if="selectedWorkspaceId && !syncApps.length" class="state">
                  暂无智能体
                </div>
                <div v-else-if="!selectedWorkspaceId" class="state">请先选择工作空间</div>
              </div>
            </div>
          </div>
          <p v-if="apiSyncError" class="state error">{{ apiSyncError }}</p>
        </div>
        <div class="modal-actions">
          <button class="ghost" type="button" @click="closeApiSyncModal">取消</button>
          <button
            class="primary"
            type="button"
            :disabled="apiSyncLoading || !selectedWorkspaceId || !selectedAppIds.length"
            @click="confirmApiSync"
          >
            {{ apiSyncLoading ? '同步中...' : '确认同步' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showAgentDeleteModal" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h3>删除智能体</h3>
          <button class="modal-close" type="button" @click="closeAgentDeleteModal">✕</button>
        </div>
        <p class="modal-body">
          确认删除 <strong>{{ agentDeleteTarget?.name }}</strong> 吗？该智能体的权限数据将一并删除。
        </p>
        <div class="modal-actions">
          <button class="ghost" type="button" @click="closeAgentDeleteModal">取消</button>
          <button
            class="primary"
            type="button"
            :disabled="agentDeleteLoading"
            @click="confirmDeleteAgent"
          >
            {{ agentDeleteLoading ? '处理中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div>
          <h2>角色管理</h2>
          <p>创建角色并维护权限模板。</p>
        </div>
      </div>

      <div class="panel role-panel">
        <div class="user-toolbar">
          <div class="search-box">
            <input v-model="roleSearch" type="text" placeholder="搜索角色名称" />
          </div>
          <div class="toolbar-actions">
            <button class="primary" type="button" @click="showRoleForm = !showRoleForm">
              {{ showRoleForm ? '收起' : '新增角色' }}
            </button>
          </div>
        </div>

        <div v-if="showRoleForm" class="user-form-panel">
          <form class="form" @submit.prevent="handleCreateRole">
            <div class="field">
              <label>角色名称</label>
              <input v-model="roleForm.name" type="text" placeholder="ops" required />
            </div>
            <div class="field">
              <label>角色描述</label>
              <input v-model="roleForm.description" type="text" placeholder="运营角色" />
            </div>
            <div class="button-row">
              <button class="primary" type="submit" :disabled="roleLoading">
                {{ roleLoading ? '保存中...' : '保存角色' }}
              </button>
            </div>
          </form>
        </div>

        <p v-if="roleError" class="state error">{{ roleError }}</p>
        <p v-if="roleSuccess" class="state success">{{ roleSuccess }}</p>

        <div v-if="rolesLoading" class="state">加载角色中...</div>
        <div v-else-if="rolesError" class="state error">{{ rolesError }}</div>
        <div v-else class="role-list">
          <div v-if="filteredRoleList.length" class="grid">
            <div v-for="role in filteredRoleList" :key="role.id" class="policy-card">
              <div>
                <h3>{{ role.name }}</h3>
                <p>{{ role.description || '暂无描述' }}</p>
              </div>
              <div class="policy-actions">
                <button
                  class="ghost danger"
                  type="button"
                  :disabled="isProtectedRole(role.name)"
                  @click="openDeleteRole(role)"
                >
                  {{ isProtectedRole(role.name) ? '系统角色不可删除' : '删除角色' }}
                </button>
              </div>
            </div>
          </div>
          <div v-else class="state">暂无角色</div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div>
          <h2>权限管理</h2>
          <p>菜单权限与资源权限可直接勾选并保存。</p>
        </div>
      </div>

      <div class="panel permission-board">
        <div class="permission-header">
          <div class="tab-group">
            <button
              class="tab"
              :class="{ active: subjectTab === 'user' }"
              type="button"
              @click="subjectTab = 'user'"
            >
              用户
            </button>
            <button
              class="tab"
              :class="{ active: subjectTab === 'role' }"
              type="button"
              @click="subjectTab = 'role'"
            >
              角色
            </button>
          </div>
          <div class="tab-group">
            <button
              class="tab"
              :class="{ active: scopeTab === 'menu' }"
              type="button"
              @click="scopeTab = 'menu'"
            >
              菜单权限
            </button>
            <button
              class="tab"
              :class="{ active: scopeTab === 'resource' }"
              type="button"
              @click="scopeTab = 'resource'"
            >
              资源权限
            </button>
          </div>
          <button
            class="primary"
            type="button"
            :disabled="permissionSaving || !selectedSubjectId || subjectReadOnly || isAdminSubject"
            @click="handleSavePermissions"
          >
            {{ permissionSaving ? '保存中...' : '保存' }}
          </button>
        </div>

        <p v-if="permissionError" class="state error">{{ permissionError }}</p>
        <p v-if="permissionSuccess" class="state success">{{ permissionSuccess }}</p>
        <p v-if="isAdminSubject" class="state">admin 默认拥有全部权限，无需配置。</p>
        <p v-if="subjectReadOnly && !isAdminSubject" class="state">
          {{ subjectTab === 'role' ? '系统角色权限不可修改。' : '该用户为超级管理员，权限不可修改。' }}
        </p>

        <div class="permission-body">
          <aside class="permission-column subject-column">
            <div class="column-title">{{ subjectTab === 'user' ? '用户' : '角色' }}</div>
          <div class="search-box compact">
            <input v-model="subjectSearch" type="text" placeholder="搜索" />
          </div>
          <p v-if="subjectTab === 'user' && usersLoading" class="state">加载用户中...</p>
          <p v-if="subjectTab === 'user' && usersError" class="state error">{{ usersError }}</p>
          <p v-if="subjectTab === 'role' && rolesLoading" class="state">加载角色中...</p>
          <p v-if="subjectTab === 'role' && rolesError" class="state error">{{ rolesError }}</p>
          <div v-if="subjectTab === 'user'" class="list">
            <button
              v-for="user in filteredSubjects"
              :key="user.id"
              class="list-item subject-item"
                :class="{ active: selectedSubjectId === String(user.id) }"
                type="button"
                @click="selectedSubjectId = String(user.id)"
              >
                <div class="subject-line">
                  <strong>{{ user.username }}</strong>
                  <span class="subject-account">{{ user.account }}</span>
                </div>
              </button>
            </div>
          <div v-else class="list">
            <button
              v-for="role in filteredSubjects"
              :key="role.id"
              class="list-item role-item"
              :class="{ active: selectedSubjectId === role.name }"
              type="button"
              @click="selectedSubjectId = role.name"
            >
              <strong>{{ role.name }}</strong>
              <small>{{ role.description || '暂无描述' }}</small>
            </button>
          </div>
          </aside>

          <aside class="permission-column scope-column">
            <div class="column-title">
              {{ scopeTab === 'menu' ? '菜单权限' : '资源分类' }}
            </div>
            <div class="list">
              <button
                v-for="item in scopeItems"
                :key="item.id"
                class="list-item"
                :class="{ active: selectedScopeId === item.id }"
                type="button"
                @click="selectedScopeId = item.id"
              >
                <strong>{{ item.label }}</strong>
                <small>{{ item.subLabel }}</small>
              </button>
            </div>
          </aside>

          <section class="permission-column table-column">
            <div class="table-toolbar">
              <input v-model="tableSearch" type="text" placeholder="搜索名称" />
            </div>

            <div v-if="permissionsLoading" class="state">加载授权中...</div>
            <div v-else-if="permissionsError" class="state error">{{ permissionsError }}</div>

            <div v-else class="table permission-grid">
              <div class="table-head permission-row">
                <div class="col col-name">资源名称</div>
                <div class="col col-action">查看</div>
                <div class="col col-action">编辑</div>
                <div class="col col-action">管理</div>
              </div>
              <div v-if="filteredRows.length" class="table-body">
                <div v-for="row in filteredRows" :key="row.key" class="table-row permission-row">
                  <div class="col col-name">
                    <span class="row-title">{{ row.label }}</span>
                    <small v-if="row.subLabel">{{ row.subLabel }}</small>
                  </div>
                  <div class="col col-action">
                    <input
                      type="checkbox"
                      :disabled="isActionDisabled(row, 'view')"
                      :checked="isRowChecked(row, 'view')"
                      @change="toggleRowAction(row, 'view', $event)"
                    />
                  </div>
                  <div class="col col-action">
                    <input
                      type="checkbox"
                      :disabled="isActionDisabled(row, 'edit')"
                      :checked="isRowChecked(row, 'edit')"
                      @change="toggleRowAction(row, 'edit', $event)"
                    />
                  </div>
                  <div class="col col-action">
                    <input
                      type="checkbox"
                      :disabled="isActionDisabled(row, 'manage')"
                      :checked="isRowChecked(row, 'manage')"
                      @change="toggleRowAction(row, 'manage', $event)"
                    />
                  </div>
                </div>
              </div>
              <div v-else class="state">暂无资源</div>
            </div>
          </section>
        </div>
      </div>

      <div class="panel">
        <div class="section-header">
          <div>
            <h3>智能体管理</h3>
            <p>新增、删除智能体，并维护分组。</p>
          </div>
        </div>

        <div class="sub-panel">
          <div class="sub-header">
            <h4>智能体管理</h4>
            <p>仅管理员可管理智能体，其他角色需授权。</p>
          </div>
          <form class="form agent-form" @submit.prevent="handleCreateAgentAdmin">
            <div class="field">
              <label>名称</label>
              <input v-model="agentForm.name" type="text" placeholder="Agent Name" required />
            </div>
            <div class="field">
              <label>URL</label>
              <input v-model="agentForm.url" type="text" placeholder="https://example.com/agent" required />
            </div>
            <div class="field">
              <label>负责人</label>
              <input v-model="agentForm.owner" type="text" placeholder="system" />
            </div>
            <div class="field">
              <label>状态</label>
              <div class="inline-dropdown" @click.stop>
                <button class="filter-trigger inline-trigger" type="button" @click.stop="toggleAgentStatusDropdown">
                  <span>{{ agentForm.status }}</span>
                  <span class="caret" :class="{ open: agentStatusOpen }"></span>
                </button>
                <div v-if="agentStatusOpen" class="filter-dropdown inline-dropdown-panel">
                  <button class="filter-option" type="button" @click="setAgentStatus('active')">
                    active
                  </button>
                  <button class="filter-option" type="button" @click="setAgentStatus('paused')">
                    paused
                  </button>
                </div>
              </div>
            </div>
            <div class="field">
              <label>描述</label>
              <input v-model="agentForm.description" type="text" placeholder="简短说明" />
            </div>
            <div class="field">
              <label>分组</label>
              <div class="combo-wrap" ref="agentGroupDropdownRef">
                <div class="combo-input" @click="focusAgentGroupInput">
                  <template v-for="group in agentForm.groups" :key="group">
                    <span class="chip">
                      {{ group }}
                      <button class="chip-remove" type="button" @click.stop="removeAgentGroup(group)">
                        ×
                      </button>
                    </span>
                  </template>
                  <input
                    ref="agentGroupInputRef"
                    v-model="agentGroupQuery"
                    type="text"
                    :placeholder="agentForm.groups.length ? '' : '输入或选择分组'"
                    @focus="openAgentGroupDropdown"
                    @keydown.enter.prevent="handleAgentGroupEnter"
                  />
                  <span v-if="agentForm.groups.length" class="combo-more">...</span>
                  <span class="combo-caret" :class="{ open: agentGroupDropdownOpen }"></span>
                </div>
                <div v-if="agentGroupDropdownOpen" class="dropdown" @click.stop>
                  <button
                    v-for="group in filteredAgentGroups"
                    :key="group"
                    type="button"
                    class="dropdown-item"
                    @click="selectAgentGroup(group)"
                  >
                    <span>{{ group }}</span>
                    <span class="dropdown-check">
                      <input type="checkbox" :checked="agentForm.groups.includes(group)" disabled />
                    </span>
                  </button>
                  <p v-if="!filteredAgentGroups.length" class="dropdown-empty">
                    {{ agentGroupQuery.trim() ? '按回车创建新分组' : '暂无可用分组' }}
                  </p>
                </div>
              </div>
            </div>
            <div class="button-row">
              <button class="primary" type="submit" :disabled="agentCreateLoading || !isAdmin">
                {{ agentCreateLoading ? '保存中...' : '新增智能体' }}
              </button>
            </div>
          </form>

          <p v-if="!isAdmin" class="state">仅管理员可新增或删除智能体。</p>
          <p v-if="agentCreateError" class="state error">{{ agentCreateError }}</p>
          <p v-if="agentCreateSuccess" class="state success">{{ agentCreateSuccess }}</p>
          <p v-if="agentDeleteError" class="state error">{{ agentDeleteError }}</p>

          <div v-if="agents.length" class="grid">
            <div v-for="agent in agents" :key="agent.id" class="policy-card">
              <div>
                <h3>{{ agent.name }}</h3>
                <p>{{ agent.description || agent.url }}</p>
              </div>
              <div class="policy-actions">
                <button
                  class="ghost danger"
                  type="button"
                  :disabled="agentDeleteLoading || !isAdmin"
                  @click="openDeleteAgent(agent)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="sub-panel">
          <div class="sub-header">
            <h4>分组管理</h4>
            <p>创建与维护可用于授权的分组。</p>
          </div>
          <form class="form" @submit.prevent="handleCreateGroup">
            <div class="field">
              <label>分组名称</label>
              <input v-model="groupForm.name" type="text" placeholder="operations" required />
            </div>
            <div class="field">
              <label>分组描述</label>
              <input v-model="groupForm.description" type="text" placeholder="运营团队" />
            </div>
            <div class="button-row">
              <button class="primary" type="submit" :disabled="groupLoading">
                {{ groupLoading ? '保存中...' : '新增分组' }}
              </button>
            </div>
          </form>

          <p v-if="groupError" class="state error">{{ groupError }}</p>
          <p v-if="groupSuccess" class="state success">{{ groupSuccess }}</p>
          <p v-if="groupsLoading" class="state">加载分组中...</p>
          <p v-if="groupsError" class="state error">{{ groupsError }}</p>

          <div v-if="groups.length" class="grid">
            <div v-for="group in groups" :key="group.id" class="policy-card">
              <div>
                <h3>{{ group.name }}</h3>
                <p>{{ group.description || '暂无描述' }}</p>
              </div>
              <div class="policy-actions">
              <button class="ghost danger" type="button" @click="openDeleteGroup(group)">
                删除
              </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header">
        <div>
          <h2>智能体接入</h2>
          <p>填写 API 域名与 Token，保存后可选择工作空间并同步智能体。</p>
        </div>
      </div>

      <div class="panel">
        <form class="form api-config-form" @submit.prevent="handleSaveApiConfig">
          <div class="field">
            <label>API 域名</label>
            <input v-model="fitSyncForm.base_url" type="text" placeholder="https://mk-ee.fit2cloud.cn" />
          </div>
          <div class="field">
            <label>Token</label>
            <input v-model="fitSyncForm.token" type="password" placeholder="Bearer token" />
          </div>
          <div class="button-row">
            <button class="primary" type="submit" :disabled="apiConfigLoading || !isAdmin">
              {{ apiConfigLoading ? '保存中...' : selectedApiConfigId ? '更新配置' : '保存配置' }}
            </button>
          </div>
        </form>

        <p v-if="!isAdmin" class="state">仅管理员可执行同步。</p>
        <p v-if="apiConfigError" class="state error">{{ apiConfigError }}</p>
        <p v-if="apiConfigSuccess" class="state success">{{ apiConfigSuccess }}</p>
        <p v-if="apiSyncError" class="state error">{{ apiSyncError }}</p>
        <p v-if="apiSyncSuccess" class="state success">{{ apiSyncSuccess }}</p>

        <div v-if="apiConfigs.length" class="grid compact-grid">
          <div v-for="config in apiConfigs" :key="config.id" class="policy-card">
            <div>
              <h3>{{ config.base_url }}</h3>
              <p>Token：{{ config.token_hint }}</p>
            </div>
            <div class="policy-actions">
              <button class="ghost" type="button" @click="selectApiConfig(config)">编辑</button>
              <button class="ghost" type="button" :disabled="!isAdmin" @click="openApiSyncModal(config)">
                同步
              </button>
              <button class="ghost danger" type="button" @click="openDeleteApiConfig(config)">
                删除
              </button>
            </div>
          </div>
        </div>
      </div>

      
    </div>

    
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  createAgent,
  deleteAgent,
  fetchAgents,
  type AgentSummary,
} from '../../services/agents'
import { fetchModels, type ModelSummary } from '../../services/models'
import {
  fetchUsers,
  createUser,
  updateUser,
  fetchRoles,
  createRole,
  deleteRole,
  fetchSubjectPermissions,
  updateSubjectPermissions,
  resetUserPassword,
  deleteUser,
  fetchAgentGroups,
  createAgentGroup,
  deleteAgentGroup,
  fetchAgentApiConfigs,
  createAgentApiConfig,
  updateAgentApiConfig,
  deleteAgentApiConfig,
  fetchFit2CloudWorkspaces,
  fetchFit2CloudApplications,
  syncFit2CloudByConfig,
  type PermissionSubjectMatrixItem,
  type Role,
  type AdminUser,
  type AgentGroup,
  type AgentApiConfig,
  type Fit2CloudWorkspace,
  type Fit2CloudApplication,
} from '../../services/admin'

type PermissionAction = 'view' | 'edit' | 'manage'
type PermissionActionState = Record<PermissionAction, boolean>

type PermissionRow = {
  key: string
  label: string
  subLabel?: string
  scope: 'menu' | 'resource'
  resourceType: string
  resourceId: string | null
}

type ScopeItem = {
  id: string
  label: string
  subLabel: string
}

const roles = ref<Role[]>([])
const users = ref<AdminUser[]>([])
const agents = ref<AgentSummary[]>([])
const models = ref<ModelSummary[]>([])
const groups = ref<AgentGroup[]>([])

const usersLoading = ref(false)
const usersError = ref('')
const rolesLoading = ref(false)
const rolesError = ref('')
const groupsLoading = ref(false)
const groupsError = ref('')
const permissionsLoading = ref(false)
const permissionsError = ref('')
const inheritedState = ref<Record<string, PermissionActionState>>({})
const subjectReadOnly = ref(false)

const roleLoading = ref(false)
const roleError = ref('')
const roleSuccess = ref('')
const showRoleForm = ref(false)

const groupLoading = ref(false)
const groupError = ref('')
const groupSuccess = ref('')

const showResetModal = ref(false)
const resetTarget = ref<AdminUser | null>(null)
const resetting = ref(false)
const showDeleteModal = ref(false)
const deleteTarget = ref<AdminUser | null>(null)
const deleting = ref(false)
const showRoleDeleteModal = ref(false)
const roleDeleteTarget = ref<Role | null>(null)
const roleDeleting = ref(false)
const showGroupDeleteModal = ref(false)
const groupDeleteTarget = ref<AgentGroup | null>(null)
const groupDeleting = ref(false)
const showAgentDeleteModal = ref(false)
const agentDeleteTarget = ref<AgentSummary | null>(null)
const showApiDeleteModal = ref(false)
const apiDeleteTarget = ref<AgentApiConfig | null>(null)

const permissionSaving = ref(false)
const permissionError = ref('')
const permissionSuccess = ref('')

 

const roleLocal = ref(localStorage.getItem('user_role') || '')
const isAdmin = computed(() => roleLocal.value === 'admin')

const apiConfigLoading = ref(false)
const apiConfigError = ref('')
const apiConfigSuccess = ref('')
const apiSyncLoading = ref(false)
const apiSyncError = ref('')
const apiSyncSuccess = ref('')
const apiConfigs = ref<AgentApiConfig[]>([])
const selectedApiConfigId = ref<number | null>(null)
const fitSyncForm = ref({
  base_url: '',
  token: '',
})
const showApiSyncModal = ref(false)
const apiSyncTarget = ref<AgentApiConfig | null>(null)
const syncWorkspaces = ref<Fit2CloudWorkspace[]>([])
const syncApps = ref<Fit2CloudApplication[]>([])
const syncWorkspaceLoading = ref(false)
const syncAppsLoading = ref(false)
const syncWorkspaceError = ref('')
const syncAppsError = ref('')
const selectedWorkspaceId = ref('')
const selectedWorkspaceName = ref('')
const selectedAppIds = ref<string[]>([])

const agentCreateLoading = ref(false)
const agentCreateError = ref('')
const agentCreateSuccess = ref('')
const agentDeleteError = ref('')
const agentDeleteLoading = ref(false)
const agentStatusOpen = ref(false)
const agentGroupQuery = ref('')
const agentGroupDropdownOpen = ref(false)
const agentGroupDropdownRef = ref<HTMLElement | null>(null)
const agentGroupInputRef = ref<HTMLInputElement | null>(null)
const agentForm = ref({
  name: '',
  url: '',
  owner: '',
  status: 'active',
  description: '',
  groups: [] as string[],
})

const userLoading = ref(false)
const userError = ref('')
const userSuccess = ref('')
const userSearch = ref('')
const userFilterField = ref<'username' | 'account'>('username')
const showUserForm = ref(false)
const roleSearch = ref('')
const filterOpen = ref(false)
const filterRef = ref<HTMLElement | null>(null)
const statusOpenFor = ref<number | null>(null)
const roleOpenFor = ref<number | null>(null)

const subjectTab = ref<'user' | 'role'>('user')
const scopeTab = ref<'menu' | 'resource'>('menu')
const subjectSearch = ref('')
const tableSearch = ref('')
const selectedSubjectId = ref('')
const selectedScopeId = ref('agents')
const permissionState = ref<Record<string, PermissionActionState>>({})

const roleForm = ref({
  name: '',
  description: '',
})

const groupForm = ref({
  name: '',
  description: '',
})

 

const userForm = ref({
  account: '',
  username: '',
  email: '',
  password: '',
  role: 'user',
  status: 'active',
  source: 'local',
  workspace: 'default',
})

const filteredUsers = computed(() => {
  const query = userSearch.value.trim().toLowerCase()
  if (!query) return users.value
  return users.value.filter((user) => {
    const field = userFilterField.value === 'account' ? user.account : user.username
    return String(field || '').toLowerCase().includes(query)
  })
})

const menuScopeItems: ScopeItem[] = [
  { id: 'all', label: '全部菜单', subLabel: '管理所有模块' },
  { id: 'agents', label: '智能体模块', subLabel: '管理与调度' },
  { id: 'models', label: '模型模块', subLabel: '能力与成本' },
  { id: 'admin', label: '权限模块', subLabel: '策略与接入' },
]

const resourceScopeItems: ScopeItem[] = [
  { id: 'agent', label: '智能体', subLabel: '具体智能体资源' },
  { id: 'agent_group', label: '智能体分组', subLabel: '按分组授权' },
  { id: 'model', label: '模型', subLabel: '具体模型资源' },
]

const scopeItems = computed(() => (scopeTab.value === 'menu' ? menuScopeItems : resourceScopeItems))

const filteredSubjects = computed(() => {
  const query = subjectSearch.value.trim().toLowerCase()
  if (subjectTab.value === 'user') {
    if (!query) return users.value
    return users.value.filter((user) => {
      const fields = [user.username, user.account, user.email]
      return fields.some((field) => String(field || '').toLowerCase().includes(query))
    })
  }

  if (!query) return roles.value
  return roles.value.filter((role) => {
    const fields = [role.name, role.description]
    return fields.some((field) => String(field || '').toLowerCase().includes(query))
  })
})

const filteredRoleList = computed(() => {
  const query = roleSearch.value.trim().toLowerCase()
  if (!query) return roles.value
  return roles.value.filter((role) =>
    String(role.name || '').toLowerCase().includes(query)
  )
})

const protectedRoles = new Set(['admin', 'user'])
const isProtectedRole = (name: string) => protectedRoles.has(name)
const selectedRole = computed(() =>
  roles.value.find((role) => role.name === selectedSubjectId.value) || null
)
const selectedUser = computed(() =>
  users.value.find((user) => String(user.id) === selectedSubjectId.value) || null
)
const isAdminSubject = computed(() => subjectTab.value === 'role' && selectedSubjectId.value === 'admin')

const buildRowKey = (scope: string, resourceType: string, resourceId: string | null) =>
  `${scope}::${resourceType}::${resourceId ?? '*'}`

const allMenuRows = computed<PermissionRow[]>(() =>
  menuScopeItems
    .filter((item) => item.id !== 'all')
    .map((item) => ({
      key: buildRowKey('menu', 'menu', item.id),
      label: item.label,
      subLabel: item.subLabel,
      scope: 'menu',
      resourceType: 'menu',
      resourceId: item.id,
    }))
)

const agentGroups = computed(() =>
  groups.value.map((group) => group.name).filter(Boolean)
)

const allResourceRows = computed<PermissionRow[]>(() => {
  const rows: PermissionRow[] = []
  const agentHeader: PermissionRow = {
    key: buildRowKey('resource', 'agent', null),
    label: '全部智能体',
    subLabel: '通配所有智能体',
    scope: 'resource',
    resourceType: 'agent',
    resourceId: null,
  }
  rows.push(agentHeader)
  agents.value.forEach((agent) => {
    rows.push({
      key: buildRowKey('resource', 'agent', agent.id),
      label: agent.name,
      subLabel: agent.owner ? `Owner: ${agent.owner}` : agent.id,
      scope: 'resource',
      resourceType: 'agent',
      resourceId: agent.id,
    })
  })

  const modelHeader: PermissionRow = {
    key: buildRowKey('resource', 'model', null),
    label: '全部模型',
    subLabel: '通配所有模型',
    scope: 'resource',
    resourceType: 'model',
    resourceId: null,
  }
  rows.push(modelHeader)
  models.value.forEach((model) => {
    rows.push({
      key: buildRowKey('resource', 'model', model.id),
      label: model.name,
      subLabel: model.provider || model.id,
      scope: 'resource',
      resourceType: 'model',
      resourceId: model.id,
    })
  })

  const groupHeader: PermissionRow = {
    key: buildRowKey('resource', 'agent_group', null),
    label: '全部分组',
    subLabel: '通配所有分组',
    scope: 'resource',
    resourceType: 'agent_group',
    resourceId: null,
  }
  rows.push(groupHeader)
  agentGroups.value.forEach((group) => {
    rows.push({
      key: buildRowKey('resource', 'agent_group', group),
      label: group,
      subLabel: '智能体分组',
      scope: 'resource',
      resourceType: 'agent_group',
      resourceId: group,
    })
  })

  return rows
})

const allRows = computed(() => [...allMenuRows.value, ...allResourceRows.value])

const rowMetaMap = computed(() => {
  const map = new Map<string, PermissionRow>()
  allRows.value.forEach((row) => {
    map.set(row.key, row)
  })
  return map
})

const tableRows = computed(() => {
  if (scopeTab.value === 'menu') {
    if (selectedScopeId.value === 'all') {
      return allMenuRows.value
    }
    return allMenuRows.value.filter((row) => row.resourceId === selectedScopeId.value)
  }
  return allResourceRows.value.filter((row) => row.resourceType === selectedScopeId.value)
})

const filteredRows = computed(() => {
  const query = tableSearch.value.trim().toLowerCase()
  if (!query) return tableRows.value
  return tableRows.value.filter((row) =>
    [row.label, row.subLabel, row.resourceId]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(query))
  )
})

const loadUsers = async () => {
  usersLoading.value = true
  usersError.value = ''
  try {
    users.value = await fetchUsers()
  } catch (err) {
    usersError.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    usersLoading.value = false
  }
}

const loadRoles = async () => {
  rolesLoading.value = true
  rolesError.value = ''
  try {
    roles.value = await fetchRoles()
  } catch (err) {
    rolesError.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    rolesLoading.value = false
  }
}

const applyPermissionSummary = (summary: PermissionSubjectSummary | null) => {
  permissionState.value = {}
  inheritedState.value = {}
  subjectReadOnly.value = summary?.read_only ?? false
  if (!summary) return
  summary.items.forEach((item: PermissionSubjectMatrixItem) => {
    const key = buildRowKey(summary.scope, item.resource_type, item.resource_id)
    permissionState.value[key] = { view: false, edit: false, manage: false }
    item.actions.forEach((action) => {
      permissionState.value[key][action] = true
    })
    if (item.inherited_actions && item.inherited_actions.length) {
      inheritedState.value[key] = { view: false, edit: false, manage: false }
      item.inherited_actions.forEach((action) => {
        inheritedState.value[key][action] = true
      })
    }
  })
}

const loadSubjectPermissions = async () => {
  if (!selectedSubjectId.value) {
    applyPermissionSummary(null)
    permissionsLoading.value = false
    return
  }
  permissionsLoading.value = true
  permissionsError.value = ''
  try {
    const summary = await fetchSubjectPermissions({
      subject_type: subjectTab.value,
      subject_id: selectedSubjectId.value,
      scope: scopeTab.value,
    })
    applyPermissionSummary(summary)
  } catch (err) {
    permissionsError.value = err instanceof Error ? err.message : '加载失败'
    applyPermissionSummary(null)
  } finally {
    permissionsLoading.value = false
  }
}

const loadAgentGroups = async () => {
  groupsLoading.value = true
  groupsError.value = ''
  try {
    groups.value = await fetchAgentGroups()
  } catch (err) {
    groupsError.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    groupsLoading.value = false
  }
}

const handleCreateRole = async () => {
  roleLoading.value = true
  roleError.value = ''
  roleSuccess.value = ''
  try {
    await createRole(roleForm.value)
    roleSuccess.value = '角色已创建。'
    roleForm.value = { name: '', description: '' }
    await loadRoles()
  } catch (err) {
    roleError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    roleLoading.value = false
  }
}

const handleCreateGroup = async () => {
  groupLoading.value = true
  groupError.value = ''
  groupSuccess.value = ''
  try {
    await createAgentGroup(groupForm.value)
    groupSuccess.value = '分组已创建。'
    groupForm.value = { name: '', description: '' }
    await loadAgentGroups()
  } catch (err) {
    groupError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    groupLoading.value = false
  }
}

const openDeleteGroup = (group: AgentGroup) => {
  groupDeleteTarget.value = group
  showGroupDeleteModal.value = true
}

const closeGroupDeleteModal = () => {
  showGroupDeleteModal.value = false
  groupDeleteTarget.value = null
}

const confirmDeleteGroup = async () => {
  if (!groupDeleteTarget.value) return
  groupDeleting.value = true
  groupsError.value = ''
  try {
    await deleteAgentGroup(groupDeleteTarget.value.id)
    closeGroupDeleteModal()
    await loadAgentGroups()
  } catch (err) {
    groupsError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    groupDeleting.value = false
  }
}

const loadApiConfigs = async () => {
  apiConfigError.value = ''
  try {
    apiConfigs.value = await fetchAgentApiConfigs()
  } catch (err) {
    apiConfigError.value = err instanceof Error ? err.message : '加载失败'
    apiConfigs.value = []
  }
}

const selectApiConfig = (config: AgentApiConfig) => {
  selectedApiConfigId.value = config.id
  fitSyncForm.value = {
    base_url: config.base_url,
    token: '',
  }
}

const handleSaveApiConfig = async () => {
  apiConfigError.value = ''
  apiConfigSuccess.value = ''
  if (!isAdmin.value) {
    apiConfigError.value = '仅管理员可保存配置。'
    return
  }
  if (!fitSyncForm.value.base_url || !fitSyncForm.value.token) {
    apiConfigError.value = '请填写 API 域名与 Token。'
    return
  }
  apiConfigLoading.value = true
  try {
    if (selectedApiConfigId.value) {
      await updateAgentApiConfig(selectedApiConfigId.value, {
        base_url: fitSyncForm.value.base_url,
        token: fitSyncForm.value.token,
      })
    } else {
      await createAgentApiConfig({
        base_url: fitSyncForm.value.base_url,
        token: fitSyncForm.value.token,
      })
    }
    apiConfigSuccess.value = '配置已保存。'
    selectedApiConfigId.value = null
    fitSyncForm.value.token = ''
    await loadApiConfigs()
  } catch (err) {
    apiConfigError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    apiConfigLoading.value = false
  }
}

const openDeleteApiConfig = (config: AgentApiConfig) => {
  groupDeleteTarget.value = null
  apiDeleteTarget.value = config
  showApiDeleteModal.value = true
}

const closeApiDeleteModal = () => {
  showApiDeleteModal.value = false
  apiDeleteTarget.value = null
}

const confirmDeleteApiConfig = async () => {
  if (!apiDeleteTarget.value) return
  apiConfigLoading.value = true
  apiConfigError.value = ''
  try {
    await deleteAgentApiConfig(apiDeleteTarget.value.id)
    closeApiDeleteModal()
    await loadApiConfigs()
  } catch (err) {
    apiConfigError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    apiConfigLoading.value = false
  }
}

const resetApiSyncState = () => {
  syncWorkspaceError.value = ''
  syncAppsError.value = ''
  syncWorkspaceLoading.value = false
  syncAppsLoading.value = false
  syncWorkspaces.value = []
  syncApps.value = []
  selectedWorkspaceId.value = ''
  selectedWorkspaceName.value = ''
  selectedAppIds.value = []
}

const openApiSyncModal = async (config: AgentApiConfig) => {
  if (!isAdmin.value) {
    apiSyncError.value = '仅管理员可执行同步。'
    return
  }
  apiSyncError.value = ''
  apiSyncSuccess.value = ''
  apiSyncTarget.value = config
  showApiSyncModal.value = true
  resetApiSyncState()
  syncWorkspaceLoading.value = true
  try {
    syncWorkspaces.value = await fetchFit2CloudWorkspaces(config.id)
  } catch (err) {
    syncWorkspaceError.value = err instanceof Error ? err.message : '加载工作空间失败'
  } finally {
    syncWorkspaceLoading.value = false
  }
}

const closeApiSyncModal = () => {
  showApiSyncModal.value = false
  apiSyncTarget.value = null
  resetApiSyncState()
}

const selectWorkspace = async (workspace: Fit2CloudWorkspace) => {
  if (!apiSyncTarget.value) return
  selectedWorkspaceId.value = workspace.id
  selectedWorkspaceName.value = workspace.name
  selectedAppIds.value = []
  syncApps.value = []
  syncAppsError.value = ''
  syncAppsLoading.value = true
  try {
    syncApps.value = await fetchFit2CloudApplications(apiSyncTarget.value.id, workspace.id)
  } catch (err) {
    syncAppsError.value = err instanceof Error ? err.message : '加载应用失败'
  } finally {
    syncAppsLoading.value = false
  }
}

const toggleAppSelection = (appId: string) => {
  if (selectedAppIds.value.includes(appId)) {
    selectedAppIds.value = selectedAppIds.value.filter((id) => id !== appId)
    return
  }
  selectedAppIds.value = [...selectedAppIds.value, appId]
}

const allAppsSelected = computed(
  () => syncApps.value.length > 0 && selectedAppIds.value.length === syncApps.value.length
)

const toggleSelectAllApps = () => {
  if (allAppsSelected.value) {
    selectedAppIds.value = []
    return
  }
  selectedAppIds.value = syncApps.value.map((app) => app.id)
}

const confirmApiSync = async () => {
  if (!apiSyncTarget.value) return
  apiSyncError.value = ''
  apiSyncSuccess.value = ''
  if (!selectedWorkspaceId.value) {
    apiSyncError.value = '请选择工作空间。'
    return
  }
  if (!selectedAppIds.value.length) {
    apiSyncError.value = '请选择需要同步的智能体。'
    return
  }
  apiSyncLoading.value = true
  try {
    const result = await syncFit2CloudByConfig(apiSyncTarget.value.id, {
      workspace_id: selectedWorkspaceId.value,
      workspace_name: selectedWorkspaceName.value || undefined,
      application_ids: selectedAppIds.value,
      sync_all: allAppsSelected.value,
    })
    apiSyncSuccess.value = `同步完成：新增 ${result.imported}，更新 ${result.updated}。`
    if (result.errors?.length) {
      apiSyncError.value = result.errors.slice(0, 3).join('；')
    }
    closeApiSyncModal()
    await loadResources()
  } catch (err) {
    apiSyncError.value = err instanceof Error ? err.message : '同步失败'
  } finally {
    apiSyncLoading.value = false
  }
}

const openDeleteRole = (role: Role) => {
  if (isProtectedRole(role.name)) {
    rolesError.value = '系统角色不可删除'
    return
  }
  roleDeleteTarget.value = role
  showRoleDeleteModal.value = true
}

const closeRoleDeleteModal = () => {
  showRoleDeleteModal.value = false
  roleDeleteTarget.value = null
}

const confirmDeleteRole = async () => {
  if (!roleDeleteTarget.value) return
  roleDeleting.value = true
  rolesError.value = ''
  roleSuccess.value = ''
  try {
    await deleteRole(roleDeleteTarget.value.id)
    roleSuccess.value = `角色 ${roleDeleteTarget.value.name} 已删除。`
    closeRoleDeleteModal()
    await loadRoles()
    await loadUsers()
    await loadSubjectPermissions()
  } catch (err) {
    rolesError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    roleDeleting.value = false
  }
}

const loadResources = async () => {
  try {
    agents.value = await fetchAgents()
  } catch {
    agents.value = []
  }

  try {
    models.value = await fetchModels()
  } catch {
    models.value = []
  }
}

const ensureSubjectSelection = () => {
  if (subjectTab.value === 'user') {
    if (!users.value.length) {
      selectedSubjectId.value = ''
      return
    }
    const exists = users.value.some((user) => String(user.id) === selectedSubjectId.value)
    if (!exists) {
      selectedSubjectId.value = String(users.value[0].id)
    }
    return
  }

  if (!roles.value.length) {
    selectedSubjectId.value = ''
    return
  }
  const exists = roles.value.some((role) => role.name === selectedSubjectId.value)
  if (!exists) {
    selectedSubjectId.value = roles.value[0].name
  }
}

const ensureScopeSelection = () => {
  if (scopeTab.value === 'menu') {
    if (!menuScopeItems.some((item) => item.id === selectedScopeId.value)) {
      selectedScopeId.value = 'agents'
    }
    return
  }
  if (!resourceScopeItems.some((item) => item.id === selectedScopeId.value)) {
    selectedScopeId.value = 'agent'
  }
}

const getRowState = (row: PermissionRow) => {
  if (!permissionState.value[row.key]) {
    permissionState.value[row.key] = { view: false, edit: false, manage: false }
  }
  return permissionState.value[row.key]
}

const isRowChecked = (row: PermissionRow, action: PermissionAction) => {
  return permissionState.value[row.key]?.[action] ?? false
}

const toggleRowAction = (row: PermissionRow, action: PermissionAction, event: Event) => {
  if (isActionDisabled(row, action)) return
  const checked = (event.target as HTMLInputElement).checked
  const state = getRowState(row)
  state[action] = checked
}

const isActionDisabled = (row: PermissionRow, action: PermissionAction) => {
  if (!selectedSubjectId.value) return true
  if (permissionsLoading.value) return true
  if (subjectReadOnly.value) return true
  if (isAdminSubject.value) return true
  if (subjectTab.value === 'user' && inheritedState.value[row.key]?.[action]) return true
  return false
}

const handleSavePermissions = async () => {
  permissionError.value = ''
  permissionSuccess.value = ''

  const subjectId = selectedSubjectId.value
  if (!subjectId) {
    permissionError.value = '请选择用户或角色'
    return
  }
  if (subjectReadOnly.value || isAdminSubject.value) {
    permissionError.value = '当前对象权限不可编辑'
    return
  }

  permissionSaving.value = true
  try {
    const items: Array<{ resource_type: string; resource_id: string | null; actions: PermissionAction[] }> = []
    Object.entries(permissionState.value).forEach(([rowKey, actions]) => {
      const row = rowMetaMap.value.get(rowKey)
      if (!row) return
      const selected = (['view', 'edit', 'manage'] as PermissionAction[]).filter(
        (action) => actions[action]
      )
      if (!selected.length) return
      items.push({
        resource_type: row.resourceType,
        resource_id: row.resourceId,
        actions: selected,
      })
    })

    const summary = await updateSubjectPermissions({
      subject_type: subjectTab.value,
      subject_id: subjectId,
      scope: scopeTab.value,
      items,
    })
    applyPermissionSummary(summary)
    permissionSuccess.value = '权限已保存。'
  } catch (err) {
    permissionError.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    permissionSaving.value = false
  }
}

const handleCreateUser = async () => {
  userLoading.value = true
  userError.value = ''
  userSuccess.value = ''

  try {
    await createUser(userForm.value)
    userSuccess.value = '用户已创建。'
    userForm.value = {
      account: '',
      username: '',
      email: '',
      password: '',
      role: 'user',
      status: 'active',
      source: 'local',
      workspace: 'default',
    }
    showUserForm.value = false
    await loadUsers()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '创建失败'
  } finally {
    userLoading.value = false
  }
}

const toggleUserForm = () => {
  showUserForm.value = !showUserForm.value
}

const toggleFilter = () => {
  filterOpen.value = !filterOpen.value
}

const selectFilter = (value: 'username' | 'account') => {
  userFilterField.value = value
  filterOpen.value = false
}

const handleFilterOutside = (event: MouseEvent) => {
  const target = event.target as Node
  if (filterOpen.value && filterRef.value && !filterRef.value.contains(target)) {
    filterOpen.value = false
  }
  statusOpenFor.value = null
  roleOpenFor.value = null
  if (agentGroupDropdownOpen.value && agentGroupDropdownRef.value) {
    if (!agentGroupDropdownRef.value.contains(target)) {
      closeAgentGroupDropdown()
    }
  }
  agentStatusOpen.value = false
}

const toggleStatusDropdown = (userId: number) => {
  roleOpenFor.value = null
  statusOpenFor.value = statusOpenFor.value === userId ? null : userId
}

const toggleRoleDropdown = (userId: number) => {
  statusOpenFor.value = null
  roleOpenFor.value = roleOpenFor.value === userId ? null : userId
}

const setUserStatus = (user: AdminUser, value: string) => {
  user.status = value
  statusOpenFor.value = null
}

const setUserRole = (user: AdminUser, value: string) => {
  user.role = value
  roleOpenFor.value = null
}

const handleSyncUsers = async () => {
  userError.value = ''
  userSuccess.value = ''
  try {
    await loadUsers()
    userSuccess.value = '同步功能暂未开放，已刷新用户列表。'
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '同步失败'
  }
}

const toggleAgentStatusDropdown = () => {
  agentStatusOpen.value = !agentStatusOpen.value
}

const setAgentStatus = (value: 'active' | 'paused') => {
  agentForm.value.status = value
  agentStatusOpen.value = false
}

const openAgentGroupDropdown = () => {
  agentGroupDropdownOpen.value = true
}

const closeAgentGroupDropdown = () => {
  agentGroupDropdownOpen.value = false
}

const focusAgentGroupInput = () => {
  agentGroupInputRef.value?.focus()
  openAgentGroupDropdown()
}

const filteredAgentGroups = computed(() => {
  const query = agentGroupQuery.value.trim().toLowerCase()
  const options = groups.value.map((group) => group.name)
  return options.filter((group) => {
    if (!query) return true
    return group.toLowerCase().includes(query)
  })
})

const selectAgentGroup = (group: string) => {
  if (!agentForm.value.groups.includes(group)) {
    agentForm.value.groups.push(group)
  }
  agentGroupQuery.value = ''
}

const removeAgentGroup = (group: string) => {
  const index = agentForm.value.groups.indexOf(group)
  if (index >= 0) {
    agentForm.value.groups.splice(index, 1)
  }
}

const handleAgentGroupEnter = async () => {
  const name = agentGroupQuery.value.trim()
  if (!name) return
  if (agentForm.value.groups.includes(name)) {
    agentGroupQuery.value = ''
    return
  }
  const exists = groups.value.some((group) => group.name === name)
  if (exists) {
    selectAgentGroup(name)
    return
  }
  try {
    await createAgentGroup({ name })
    await loadAgentGroups()
    selectAgentGroup(name)
  } catch (err) {
    agentCreateError.value = err instanceof Error ? err.message : '新增分组失败'
  }
}

const handleCreateAgentAdmin = async () => {
  if (!isAdmin.value) {
    agentCreateError.value = '仅管理员可新增智能体。'
    return
  }
  agentCreateLoading.value = true
  agentCreateError.value = ''
  agentCreateSuccess.value = ''
  try {
    await createAgent({
      name: agentForm.value.name,
      url: agentForm.value.url,
      owner: agentForm.value.owner || 'system',
      status: agentForm.value.status,
      last_run: '',
      description: agentForm.value.description,
      groups: agentForm.value.groups,
    })
    agentCreateSuccess.value = '智能体已新增。'
    agentForm.value = {
      name: '',
      url: '',
      owner: '',
      status: 'active',
      description: '',
      groups: [],
    }
    agentGroupQuery.value = ''
    await loadResources()
    await loadAgentGroups()
  } catch (err) {
    agentCreateError.value = err instanceof Error ? err.message : '新增失败'
  } finally {
    agentCreateLoading.value = false
  }
}

const handleDeleteAgentAdmin = async (agent: AgentSummary) => {
  if (!isAdmin.value) {
    agentDeleteError.value = '仅管理员可删除智能体。'
    return
  }
  agentDeleteLoading.value = true
  agentDeleteError.value = ''
  try {
    await deleteAgent(agent.id)
    await loadResources()
    await loadSubjectPermissions()
  } catch (err) {
    agentDeleteError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    agentDeleteLoading.value = false
  }
}

const openDeleteAgent = (agent: AgentSummary) => {
  agentDeleteTarget.value = agent
  showAgentDeleteModal.value = true
}

const closeAgentDeleteModal = () => {
  showAgentDeleteModal.value = false
  agentDeleteTarget.value = null
}

const confirmDeleteAgent = async () => {
  if (!agentDeleteTarget.value) return
  await handleDeleteAgentAdmin(agentDeleteTarget.value)
  closeAgentDeleteModal()
}

const handleUpdateUser = async (user: AdminUser) => {
  userError.value = ''
  userSuccess.value = ''
  try {
    await updateUser(user.id, { role: user.role, status: user.status })
    userSuccess.value = `用户 ${user.username} 已更新。`
    await loadUsers()
    await loadSubjectPermissions()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '更新失败'
  }
}

const openResetPassword = (user: AdminUser) => {
  resetTarget.value = user
  showResetModal.value = true
}

const closeResetModal = () => {
  showResetModal.value = false
  resetTarget.value = null
}

const confirmResetPassword = async () => {
  if (!resetTarget.value) return
  resetting.value = true
  userError.value = ''
  userSuccess.value = ''
  try {
    await resetUserPassword(resetTarget.value.id)
    userSuccess.value = `用户 ${resetTarget.value.username} 密码已重置为 agentui@2025。`
    closeResetModal()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '重置失败'
  } finally {
    resetting.value = false
  }
}

const openDeleteUser = (user: AdminUser) => {
  deleteTarget.value = user
  showDeleteModal.value = true
}

const closeDeleteModal = () => {
  showDeleteModal.value = false
  deleteTarget.value = null
}

const confirmDeleteUser = async () => {
  if (!deleteTarget.value) return
  deleting.value = true
  userError.value = ''
  userSuccess.value = ''
  try {
    await deleteUser(deleteTarget.value.id)
    userSuccess.value = `用户 ${deleteTarget.value.username} 已删除。`
    closeDeleteModal()
    await loadUsers()
    await loadSubjectPermissions()
  } catch (err) {
    userError.value = err instanceof Error ? err.message : '删除失败'
  } finally {
    deleting.value = false
  }
}





onMounted(loadRoles)
onMounted(loadUsers)
onMounted(loadResources)
onMounted(loadAgentGroups)
onMounted(loadApiConfigs)
onMounted(() => {
  document.addEventListener('click', handleFilterOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleFilterOutside)
})

watch(
  () => subjectTab.value,
  () => {
    subjectSearch.value = ''
    ensureSubjectSelection()
    loadSubjectPermissions()
  }
)

watch(
  () => scopeTab.value,
  () => {
    ensureScopeSelection()
    loadSubjectPermissions()
  }
)

watch([users, roles], () => {
  ensureSubjectSelection()
  loadSubjectPermissions()
})

watch([selectedSubjectId], () => {
  loadSubjectPermissions()
})

watch([agents, models, groups], () => {
  if (scopeTab.value === 'resource') {
    loadSubjectPermissions()
  }
})
</script>

<style scoped>
.admin {
  display: grid;
  gap: 28px;
}

.section {
  display: grid;
  gap: 16px;
}

.section-header h2 {
  font-family: 'Space Grotesk', sans-serif;
  margin: 0 0 6px;
  font-size: 24px;
}

.section-header p {
  margin: 0;
  color: #4b5b60;
}

.panel {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  padding: 18px;
  border: 1px solid rgba(15, 40, 55, 0.18);
}

.sub-panel {
  margin-top: 14px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(15, 40, 55, 0.12);
  background: #fff;
  display: grid;
  gap: 12px;
}

.compact-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.sub-header h4 {
  margin: 0 0 4px;
  font-size: 16px;
}

.sub-header p {
  margin: 0;
  color: #6a7a80;
  font-size: 12px;
}

.user-panel {
  display: grid;
  gap: 16px;
}

.user-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 40, 55, 0.1);
  background: #fff;
  min-width: 260px;
  flex: 1;
  max-width: 360px;
}

.filter-box {
  position: relative;
}

.filter-trigger {
  border: none;
  background: rgba(15, 179, 185, 0.1);
  color: #0c7e85;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex: 0 0 auto;
  min-width: 64px;
  transition: background 0.2s ease, transform 0.2s ease;
}

.filter-trigger:hover {
  background: rgba(15, 179, 185, 0.18);
  transform: translateY(-1px);
}

.caret {
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid #0c7e85;
  transition: transform 0.2s ease;
}

.caret.open {
  transform: rotate(180deg);
}

.filter-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 110px;
  background: #fff;
  border: 1px solid rgba(15, 40, 55, 0.18);
  border-radius: 12px;
  padding: 6px;
  display: grid;
  gap: 4px;
  box-shadow: 0 12px 24px rgba(15, 40, 55, 0.12);
  z-index: 20;
}

.filter-option {
  border: none;
  background: transparent;
  text-align: left;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #2f3f44;
  cursor: pointer;
  transition: background 0.2s ease;
}

.filter-option:hover {
  background: rgba(15, 179, 185, 0.12);
}

.inline-dropdown {
  position: relative;
}

.inline-trigger {
  width: 100%;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #d6e0e2;
  color: #2f3f44;
  padding: 6px 10px;
  border-radius: 12px;
  font-weight: 500;
  min-width: 80px;
}

.inline-trigger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: #f7fafb;
}

.inline-dropdown-panel {
  width: 100%;
  min-width: 0;
}

.search-box input {
  border: none;
  outline: none;
  width: 100%;
  font-size: 14px;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}


.toolbar-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.user-form-panel {
  padding: 14px;
  border-radius: 16px;
  background: rgba(15, 179, 185, 0.06);
  border: 1px dashed rgba(15, 179, 185, 0.2);
}

.table {
  display: grid;
  gap: 8px;
  overflow-x: auto;
}

.table-head,
.table-row {
  display: grid;
  grid-template-columns: 40px 120px 140px 120px 200px 120px 120px 180px 260px;
  align-items: center;
  gap: 10px;
  min-width: 1240px;
}

.table-head {
  padding: 10px 8px;
  font-size: 12px;
  color: #6b7b82;
  border-bottom: 1px solid rgba(15, 40, 55, 0.08);
}

.table-body {
  display: grid;
  gap: 6px;
}

.table-row {
  padding: 12px 8px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid rgba(15, 40, 55, 0.06);
}

.table-row:hover {
  box-shadow: 0 10px 24px rgba(15, 40, 55, 0.08);
}

.col {
  font-size: 13px;
  color: #314046;
}

.col-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.action-control {
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.col-actions select {
  border: 1px solid #d6e0e2;
  border-radius: 10px;
  padding: 6px 8px;
  font-size: 12px;
  background: #fff;
  height: 34px;
}

.col-status select {
  border: 1px solid #d6e0e2;
  border-radius: 10px;
  padding: 6px 8px;
  font-size: 12px;
  background: #fff;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #0f6b4f;
  background: rgba(15, 107, 79, 0.12);
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.agent-form {
  grid-template-columns: repeat(7, minmax(110px, 1fr)) 140px;
  align-items: end;
  column-gap: 10px;
  row-gap: 10px;
}

.agent-form .button-row {
  flex-wrap: nowrap;
  align-items: end;
  align-self: end;
}

.agent-form .button-row .primary {
  height: 40px;
  padding: 0 16px;
}

.field {
  display: grid;
  gap: 6px;
  font-size: 13px;
  min-width: 0;
}

.field-inline {
  align-items: center;
}

.field label {
  color: #5a6a70;
}

.field input,
.field select {
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 10px 12px;
  font-size: 14px;
  height: 40px;
  box-sizing: border-box;
}

.primary {
  border: none;
  border-radius: 12px;
  padding: 10px 16px;
  font-weight: 600;
  background: linear-gradient(120deg, #0fb3b9, #5ce1e6);
  color: #fff;
  cursor: pointer;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.api-config-form {
  grid-template-columns: 1fr 1fr auto;
  align-items: end;
}

.api-config-form .button-row {
  flex-wrap: nowrap;
  align-items: end;
  align-self: end;
}

.api-config-form .button-row .primary {
  height: 40px;
  padding: 0 16px;
}

.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ghost {
  border: 1px solid rgba(15, 179, 185, 0.4);
  color: #0c7e85;
  background: transparent;
  padding: 10px 16px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 600;
}

.ghost:hover {
  background: rgba(15, 179, 185, 0.08);
}

.ghost.action-control {
  padding: 0 14px;
  height: 34px;
}

.primary.action-control {
  padding: 0 14px;
  height: 34px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(8, 18, 22, 0.35);
  display: grid;
  place-items: center;
  z-index: 50;
}

.modal-card {
  width: min(420px, 92vw);
  background: #fff;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 18px 50px rgba(15, 40, 55, 0.18);
  display: grid;
  gap: 12px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.modal-close {
  border: none;
  background: transparent;
  font-size: 16px;
  cursor: pointer;
  color: #6a7a80;
}

.modal-body {
  margin: 0;
  color: #4b5b60;
  font-size: 14px;
}

.modal-body code {
  background: rgba(15, 179, 185, 0.12);
  color: #0c7e85;
  padding: 2px 6px;
  border-radius: 6px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.state {
  font-size: 13px;
  color: #5a6a70;
  margin-top: 8px;
}

.state.error {
  color: #b13333;
}

.state.success {
  color: #0f6b4f;
}

.policy-list {
  display: grid;
  gap: 12px;
}

.policy-group {
  display: grid;
  gap: 10px;
}

.policy-group > h3 {
  margin: 8px 0 0;
  font-size: 14px;
  color: #4b5b60;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 40, 55, 0.12);
}

.policy-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  padding: 14px;
  border: 1px solid rgba(15, 40, 55, 0.14);
  display: grid;
  gap: 8px;
}

.policy-card h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.policy-card p {
  margin: 0;
  color: #6a7a80;
  font-size: 12px;
}

.policy-meta {
  font-size: 12px;
  color: #5a6a70;
  display: grid;
  gap: 4px;
}

.policy-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ghost.danger {
  border-color: rgba(255, 94, 94, 0.5);
  color: #b13333;
}

.permission-board {
  display: grid;
  gap: 16px;
  grid-template-rows: auto 1fr;
  max-height: calc(100vh - 320px);
  min-height: 320px;
  overflow: hidden;
}

.permission-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.tab-group {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  border-radius: 12px;
  background: rgba(15, 179, 185, 0.12);
}

.tab {
  border: none;
  background: transparent;
  padding: 6px 12px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  color: #4b5b60;
}

.tab.active {
  background: #fff;
  color: #0c7e85;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(15, 40, 55, 0.12);
}

.permission-body {
  display: grid;
  grid-template-columns: minmax(180px, 230px) minmax(180px, 240px) minmax(320px, 1fr);
  gap: 12px;
  min-height: 0;
  height: 100%;
}

.permission-column {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 16px;
  border: 1px solid rgba(15, 40, 55, 0.16);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.table-column {
  background: transparent;
  border: none;
  padding: 0;
}

.column-title {
  font-size: 13px;
  font-weight: 600;
  color: #3a4a4f;
}

.search-box.compact {
  min-width: 0;
  max-width: none;
  padding: 0 10px;
  height: 34px;
  align-items: center;
  flex: 0 0 auto;
  box-sizing: border-box;
  border: 1px solid rgba(15, 40, 55, 0.16);
  box-shadow: none;
  background: #fff;
  margin-bottom: 6px;
}

.search-box.compact input {
  height: 100%;
  background: transparent;
}

.list {
  display: grid;
  gap: 8px;
  overflow-y: auto;
  padding-right: 4px;
  flex: 1;
  min-height: 0;
}

.list-item {
  text-align: left;
  border: 1px solid transparent;
  background: #fff;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  display: grid;
  gap: 4px;
  box-shadow: 0 6px 14px rgba(15, 40, 55, 0.08);
  height: 60px;
}

.list-item.subject-item,
.list-item.role-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.subject-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.subject-account {
  font-size: 11px;
  color: #6a7a80;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-item strong {
  font-size: 13px;
  color: #2e3c41;
}

.list-item small {
  font-size: 11px;
  color: #6a7a80;
}

.list-item.active {
  background: rgba(15, 179, 185, 0.16);
  border-color: rgba(15, 179, 185, 0.45);
}

.role-form {
  display: grid;
  gap: 10px;
}

.role-actions {
  display: flex;
  justify-content: flex-end;
}

.compact-form {
  grid-template-columns: 1fr;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.table-toolbar input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 0 12px;
  font-size: 14px;
  height: 34px;
}

.permission-grid {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.permission-grid .table-body {
  overflow-y: auto;
  min-height: 0;
  padding-right: 4px;
  flex: 1;
}

.permission-grid .table-head,
.permission-grid .table-row {
  grid-template-columns: 1fr repeat(3, 80px);
  min-width: 520px;
}

.permission-row .col-action {
  display: flex;
  align-items: center;
  justify-content: center;
}

.permission-row input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: #0fb3b9;
}

.row-title {
  font-weight: 600;
  color: #2f3f44;
}

.permission-row small {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #6a7a80;
}

@media (max-width: 1100px) {
  .permission-body {
    grid-template-columns: 1fr;
  }
}
.combo-wrap {
  position: relative;
  width: 100%;
  min-width: 0;
}

.combo-input {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  height: 40px;
  border-radius: 12px;
  border: 1px solid #d6e0e2;
  padding: 0 10px;
  background: #fff;
  cursor: text;
  overflow: hidden;
  white-space: nowrap;
  max-width: 100%;
  box-sizing: border-box;
}

.combo-input input {
  border: none;
  outline: none;
  flex: 1 1 120px;
  min-width: 0;
  font-size: 14px;
  height: 100%;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(15, 179, 185, 0.12);
  color: #0c7e85;
  font-size: 12px;
  height: 24px;
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 0 0 auto;
}

.combo-more {
  color: #8a9aa0;
  font-size: 12px;
  margin-left: 4px;
}

.dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 80%;
  min-width: 0;
  max-width: 100%;
  background: #fff;
  border: 1px solid rgba(15, 40, 55, 0.18);
  border-radius: 12px;
  padding: 6px;
  display: grid;
  gap: 4px;
  max-height: 200px;
  overflow: auto;
  z-index: 20;
  box-shadow: 0 12px 24px rgba(15, 40, 55, 0.12);
}

.dropdown-item {
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  font-size: 13px;
  color: #2f3f44;
  transition: background 0.2s ease;
}

.dropdown-item:hover {
  background: rgba(15, 179, 185, 0.12);
}

.dropdown-empty {
  padding: 8px 10px;
  font-size: 12px;
  color: #8a9aa0;
}

.dropdown-check {
  display: inline-flex;
  align-items: center;
}

.dropdown-check input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: #0fb3b9;
}

.combo-caret {
  margin-left: auto;
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid #0c7e85;
  transition: transform 0.2s ease;
}

.combo-caret.open {
  transform: rotate(180deg);
}

.modal-card.modal-large {
  width: min(920px, 92vw);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.sync-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.sync-panel {
  border: 1px solid rgba(15, 40, 55, 0.12);
  border-radius: 16px;
  padding: 12px;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fff;
  min-height: 0;
}

.sync-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.checkbox-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4c5a60;
}

.checkbox-line input {
  width: 16px;
  height: 16px;
  accent-color: #0fb3b9;
}

.checkbox-item {
  grid-template-columns: 16px 1fr;
  gap: 10px;
  height: auto;
  align-items: center;
}

.checkbox-item input {
  width: 16px;
  height: 16px;
  accent-color: #0fb3b9;
}

.checkbox-text {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.modal-card.modal-large .modal-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.sync-panel .list {
  flex: 1;
  min-height: 0;
}
</style>
