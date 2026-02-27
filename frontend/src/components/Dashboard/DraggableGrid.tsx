import { useState } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import styles from './DraggableGrid.module.css';

interface GridItem {
  id: string;
  element: React.ReactNode;
  label: string;
}

interface SortableItemProps {
  item: GridItem;
}

function SortableItem({ item }: SortableItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className={styles.sortableWrapper}>
      <div className={styles.gripHandle} {...attributes} {...listeners}>
        ⠿
      </div>
      {item.element}
    </div>
  );
}

interface DraggableGridProps {
  items: GridItem[];
  onReorder: (ids: string[]) => void;
}

export function DraggableGrid({ items, onReorder }: DraggableGridProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const activeItem = activeId ? items.find((i) => i.id === activeId) : null;

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);

    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((i) => i.id === active.id);
      const newIndex = items.findIndex((i) => i.id === over.id);
      const newIds = arrayMove(items, oldIndex, newIndex).map((i) => i.id);
      onReorder(newIds);
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
        <div className={styles.grid}>
          {items.map((item) => (
            <SortableItem key={item.id} item={item} />
          ))}
        </div>
      </SortableContext>

      <DragOverlay>
        {activeItem ? (
          <div className={styles.dragGhost}>
            {activeItem.label}
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
