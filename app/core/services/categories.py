from __future__ import annotations

from typing import Optional

from app.core.base import iso
from app.core.services.base import BaseService


class CategoryService(BaseService):
    def category_path_ids(self, category_id: str) -> list[str]:
        path: list[str] = []
        current = self.store.categories.get(category_id)
        while current:
            path.insert(0, current['id'])
            parent_id = current.get('parent_id')
            current = self.store.categories.get(parent_id) if parent_id else None
        return path

    def category_ref(self, category_id: str) -> dict[str, object]:
        category = self.store.categories[category_id]
        path_ids = self.category_path_ids(category_id)
        return {
            'id': category['id'],
            'name': category['name'],
            'parent_id': category.get('parent_id'),
            'level': max(len(path_ids) - 1, 0),
            'path': [self.store.categories[path_id]['name'] for path_id in path_ids],
        }

    def category_ref_b2b(self, category_id: str) -> dict[str, object]:
        category = self.store.categories[category_id]
        path_ids = self.category_path_ids(category_id)
        return {
            'id': category['id'],
            'name': category['name'],
            'parent_id': category.get('parent_id'),
            'level': max(len(path_ids) - 1, 0),
            'path': '/'.join(self.store.categories[path_id]['name'].lower().replace(' ', '-') for path_id in path_ids),
            'is_active': category['is_active'],
            'created_at': iso(category['created_at']),
        }

    def category_tree_b2c(self, category_id: Optional[str] = None) -> list[dict[str, object]]:
        nodes = []
        for cat in self.store.categories.values():
            if cat.get('parent_id') == category_id:
                node = self.category_ref(cat['id'])
                node['children'] = self.category_tree_b2c(cat['id'])
                nodes.append(node)
        return sorted(nodes, key=lambda item: item['name'])

    def category_tree_b2b(self, category_id: Optional[str] = None) -> list[dict[str, object]]:
        nodes = []
        for cat in self.store.categories.values():
            if cat.get('parent_id') == category_id:
                node = {'id': cat['id'], 'name': cat['name'], 'children': self.category_tree_b2b(cat['id'])}
                nodes.append(node)
        return sorted(nodes, key=lambda item: item['name'])
